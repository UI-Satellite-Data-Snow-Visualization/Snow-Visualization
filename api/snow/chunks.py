"""Lossless 200 x 200 SQLite storage on each product’s native global grid.

A tile/year/threshold (FDL and LDS together) is committed atomically. Product
keys include collection; additional sensor grids need explicit registration.
"""

from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
import zlib

from affine import Affine
import numpy as np
import rasterio

from . import watershed as ws
from . import fdl as F

PRODUCT = "MOD10A1F.061"
CHUNK_SIZE = 200
DB_NAME = "snow.sqlite3"
SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
 product TEXT PRIMARY KEY, pixel_size REAL NOT NULL, tile_width INTEGER NOT NULL,
 origin_x REAL NOT NULL, origin_y REAL NOT NULL, chunk_size INTEGER NOT NULL,
 crs TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (
 product TEXT NOT NULL REFERENCES products(product), tile TEXT NOT NULL,
 year INTEGER NOT NULL, threshold REAL NOT NULL, provenance TEXT NOT NULL,
 PRIMARY KEY(product,tile,year,threshold));
CREATE TABLE IF NOT EXISTS chunks (
 product TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('FDL','LDS')),
 threshold REAL NOT NULL, year INTEGER NOT NULL,
 chunk_row INTEGER NOT NULL, chunk_col INTEGER NOT NULL,
 tile TEXT NOT NULL, data BLOB NOT NULL,
 PRIMARY KEY(product,kind,threshold,year,chunk_row,chunk_col),
 FOREIGN KEY(product,tile,year,threshold) REFERENCES runs(product,tile,year,threshold));
"""


@dataclass(frozen=True)
class ProductGrid:
    product: str
    pixel_size: float
    tile_width: int
    origin_x: float
    origin_y: float
    crs: rasterio.crs.CRS

    def __post_init__(self):
        if self.tile_width <= 0 or self.tile_width % CHUNK_SIZE:
            raise ValueError("Tile width must be a positive multiple of chunk size")
        if not np.isfinite(self.pixel_size) or self.pixel_size <= 0:
            raise ValueError("Pixel size must be positive and finite")
        if not np.isfinite([self.origin_x, self.origin_y]).all():
            raise ValueError("Grid origin must be finite")

    def record(self):
        return (
            self.product,
            self.pixel_size,
            self.tile_width,
            self.origin_x,
            self.origin_y,
            CHUNK_SIZE,
            self.crs.to_string(),
        )


MODIS = ProductGrid(
    PRODUCT,
    ws.PIXEL_SIZE_500M,
    ws.TILE_PIXELS_500M,
    ws.GRID_ORIGIN_X,
    ws.GRID_ORIGIN_Y,
    ws.MODIS_CRS,
)


def load_product(conn, product):
    row = conn.execute(
        "SELECT product,pixel_size,tile_width,origin_x,origin_y,chunk_size,crs FROM products WHERE product=?",
        (product,),
    ).fetchone()
    if row is None:
        raise FileNotFoundError(f"Unknown stored product: {product}")
    if row[5] != CHUNK_SIZE:
        raise ValueError("Unsupported stored chunk size")
    return ProductGrid(*row[:5], rasterio.crs.CRS.from_string(row[6]))


def database(store_dir):
    return Path(store_dir) / DB_NAME


def connect(path, *, write=False):
    path = Path(path)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        path if write else path.resolve().as_uri() + "?mode=ro",
        uri=not write,
        timeout=30,
    )
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def tile_grid(tile, product_grid=MODIS):
    if not re.fullmatch(r"h\d{2}v\d{2}", tile):
        raise ValueError(f"Invalid tile: {tile}")
    h, v = int(tile[1:3]), int(tile[4:6])
    if not (0 <= h < 36 and 0 <= v < 18):
        raise ValueError(f"Invalid tile: {tile}")
    g = product_grid
    edge = g.pixel_size * g.tile_width
    return ws.Grid(
        Affine(
            g.pixel_size,
            0,
            g.origin_x + h * edge,
            0,
            -g.pixel_size,
            g.origin_y - v * edge,
        ),
        (g.tile_width, g.tile_width),
        g.crs,
    )


def offsets(grid, product_grid=MODIS):
    t = grid.transform
    px = product_grid.pixel_size
    if grid.crs != product_grid.crs:
        raise ValueError("Grid CRS does not match product")
    if (
        t.b != 0
        or t.d != 0
        or not np.allclose([t.a, t.e], [px, -px], rtol=0, atol=1e-7)
    ):
        raise ValueError("Grid is not on the product pixel lattice")
    col, row = (t.c - product_grid.origin_x) / px, (product_grid.origin_y - t.f) / px
    if abs(col - round(col)) > 1e-3 or abs(row - round(row)) > 1e-3:
        raise ValueError("Grid is not aligned to product pixels")
    return round(row), round(col)


def write_tile(
    path,
    tile,
    year,
    threshold,
    fdl,
    lds,
    transform,
    provenance,
    *,
    overwrite=False,
    product_grid=MODIS,
):
    """Write full native tiles; preserve -1, 0 and 365 without interpretation."""
    grid = _validate_tile(tile, threshold, fdl, lds, transform, product_grid)
    metadata = _encode_provenance(provenance, transform, product_grid)
    key = (product_grid.product, tile, int(year), float(threshold))
    origin = offsets(grid, product_grid)
    with closing(connect(path, write=True)) as conn:
        conn.executescript(SCHEMA)
        with conn:
            _register_product(conn, product_grid)
            _replace_run(conn, key, metadata, overwrite)
            for kind, array in [("FDL", fdl), ("LDS", lds)]:
                conn.executemany(
                    "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?)",
                    _chunk_records(key, kind, array, origin),
                )


def _validate_tile(tile, threshold, fdl, lds, transform, product_grid):
    expected = tile_grid(tile, product_grid)
    actual = ws.Grid(transform, expected.shape, product_grid.crs)
    if offsets(actual, product_grid) != offsets(expected, product_grid):
        raise ValueError("Transform does not match the named tile")
    if not np.isfinite(threshold) or not 0 < threshold <= 100:
        raise ValueError("Threshold must be finite and in (0, 100]")
    for array in (fdl, lds):
        if array.shape != expected.shape or array.dtype != np.dtype("int16"):
            raise ValueError(
                f"Expected a full {expected.shape[0]} x {expected.shape[1]} int16 tile"
            )
    return expected


def _encode_provenance(provenance, transform, product_grid):
    metadata = dict(
        provenance,
        crs=product_grid.crs.to_string(),
        transform=list(transform),
        nodata=F.NODATA,
        storage_encoding="zlib little-endian int16 C-order",
        storage_version=1,
    )
    return json.dumps(metadata, sort_keys=True)


def _register_product(conn, product_grid):
    conn.execute(
        "INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?,?)", product_grid.record()
    )
    if load_product(conn, product_grid.product) != product_grid:
        raise ValueError("Product grid conflicts with stored metadata")


def _replace_run(conn, key, metadata, overwrite):
    """Replace one run inside the caller's transaction, including its old chunks."""
    where = "WHERE product=? AND tile=? AND year=? AND threshold=?"
    if conn.execute("SELECT 1 FROM runs " + where, key).fetchone() and not overwrite:
        _, tile, year, threshold = key
        raise FileExistsError(f"{tile} {year} threshold {threshold} already stored")
    conn.execute("DELETE FROM chunks " + where, key)
    conn.execute("DELETE FROM runs " + where, key)
    conn.execute("INSERT INTO runs VALUES (?,?,?,?,?)", (*key, metadata))


def _chunk_records(key, kind, array, origin):
    """Yield compressed database rows without collecting a second tile in memory."""
    product, tile, year, threshold = key
    origin_row, origin_col = origin
    height, width = array.shape
    for row in range(0, height, CHUNK_SIZE):
        for col in range(0, width, CHUNK_SIZE):
            chunk = array[row : row + CHUNK_SIZE, col : col + CHUNK_SIZE]
            data = zlib.compress(chunk.astype("<i2").tobytes())
            yield (
                product,
                kind,
                threshold,
                year,
                (origin_row + row) // CHUNK_SIZE,
                (origin_col + col) // CHUNK_SIZE,
                tile,
                data,
            )


def stored_years(path, tiles, threshold=10, *, product=PRODUCT):
    if not Path(path).exists() or not tiles:
        return []
    with closing(connect(path)) as conn:
        have = {}
        for year, tile in conn.execute(
            "SELECT year,tile FROM runs WHERE product=? AND threshold=?",
            (product, threshold),
        ):
            have.setdefault(year, set()).add(tile)
    return sorted(y for y, found in have.items() if set(tiles) <= found)


def read_window(path, grid, tiles, year, threshold=10, kind="FDL", *, product=PRODUCT):
    if kind not in ("FDL", "LDS"):
        raise ValueError("Kind must be FDL or LDS")
    result = np.full(grid.shape, F.NODATA, dtype=np.int16)
    with closing(connect(path)) as conn:
        product_grid = load_product(conn, product)
        origin = offsets(grid, product_grid)
        for tile in tiles:
            key = (product, tile, year, threshold)
            _require_run(conn, key, kind)
            bounds = _tile_overlap(grid.shape, origin, tile, product_grid)
            if bounds is None:
                continue
            for row, col, data in _read_chunks(conn, key, kind, bounds):
                _copy_chunk(result, origin, bounds, row, col, _decode_chunk(data))
    return result


def _require_run(conn, key, kind):
    row = conn.execute(
        "SELECT 1 FROM runs WHERE product=? AND tile=? AND year=? AND threshold=?", key
    ).fetchone()
    if row is None:
        _, tile, year, threshold = key
        raise FileNotFoundError(
            f"No stored {kind} for {tile} {year} threshold {threshold}"
        )


def _tile_overlap(shape, origin, tile, product_grid):
    """Return intersecting global pixel bounds, with exclusive bottom/right edges."""
    row, col = origin
    tile_row, tile_col = offsets(tile_grid(tile, product_grid), product_grid)
    top = max(row, tile_row)
    bottom = min(row + shape[0], tile_row + product_grid.tile_width)
    left = max(col, tile_col)
    right = min(col + shape[1], tile_col + product_grid.tile_width)
    if top >= bottom or left >= right:
        return None
    return top, bottom, left, right


def _read_chunks(conn, key, kind, bounds):
    top, bottom, left, right = bounds
    first_row, last_row = top // CHUNK_SIZE, (bottom - 1) // CHUNK_SIZE
    first_col, last_col = left // CHUNK_SIZE, (right - 1) // CHUNK_SIZE
    rows = conn.execute(
        """SELECT chunk_row,chunk_col,data FROM chunks
        WHERE product=? AND tile=? AND year=? AND threshold=? AND kind=?
        AND chunk_row BETWEEN ? AND ? AND chunk_col BETWEEN ? AND ?""",
        (*key, kind, first_row, last_row, first_col, last_col),
    ).fetchall()
    expected = (last_row - first_row + 1) * (last_col - first_col + 1)
    if len(rows) != expected:
        raise ValueError(f"Incomplete chunk data for {key[1]} {key[2]}")
    return rows


def _decode_chunk(blob):
    data = zlib.decompress(blob)
    if len(data) != CHUNK_SIZE * CHUNK_SIZE * 2:
        raise ValueError("Invalid chunk byte length")
    return np.frombuffer(data, dtype="<i2").reshape(CHUNK_SIZE, CHUNK_SIZE)


def _copy_chunk(result, origin, bounds, chunk_row, chunk_col, chunk):
    """Copy only the overlap; source and destination share the global pixel grid."""
    row, col = chunk_row * CHUNK_SIZE, chunk_col * CHUNK_SIZE
    top, bottom, left, right = bounds
    top, bottom = max(top, row), min(bottom, row + CHUNK_SIZE)
    left, right = max(left, col), min(right, col + CHUNK_SIZE)
    origin_row, origin_col = origin
    result[
        top - origin_row : bottom - origin_row, left - origin_col : right - origin_col
    ] = chunk[top - row : bottom - row, left - col : right - col]


def export_tile(path, dest, tile, year, threshold=10, kind="FDL", *, product=PRODUCT):
    with closing(connect(path)) as conn:
        product_grid = load_product(conn, product)
    grid = tile_grid(tile, product_grid)
    array = read_window(path, grid, [tile], year, threshold, kind, product=product)
    with closing(connect(path)) as conn:
        provenance = conn.execute(
            "SELECT provenance FROM runs WHERE product=? AND tile=? AND year=? AND threshold=?",
            (product, tile, year, threshold),
        ).fetchone()[0]
    with rasterio.open(
        dest,
        "w",
        driver="GTiff",
        height=grid.shape[0],
        width=grid.shape[1],
        count=1,
        dtype="int16",
        crs=grid.crs,
        transform=grid.transform,
        nodata=F.NODATA,
        compress="deflate",
        tiled=True,
    ) as dst:
        dst.write(array, 1)
        dst.update_tags(
            product=product,
            tile=tile,
            year=year,
            threshold=threshold,
            kind=kind,
            provenance=provenance,
        )
