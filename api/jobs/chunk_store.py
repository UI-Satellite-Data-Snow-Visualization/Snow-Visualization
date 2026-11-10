"""Import existing full MODIS GeoTIFF pairs, or export SQLite chunks for inspection."""

import argparse
import hashlib
import re
from pathlib import Path
import time

import numpy as np
import rasterio

from config import FDL_STORE_DIR
from snow import chunks
from snow import watershed as ws


def import_pair(path, fdl_path, *, overwrite=False):
    match = re.fullmatch(r"fdl_(h\d{2}v\d{2})_(\d{4})_t([\d.]+)\.tif", fdl_path.name)
    if not match:
        raise ValueError(f"Unrecognized FDL filename: {fdl_path.name}")
    tile, year, threshold = match[1], int(match[2]), float(match[3])
    if year in chunks.stored_years(path, [tile], threshold) and not overwrite:
        print(f"{fdl_path.name}: already imported")
        return
    arrays, provenance = _read_pair(fdl_path, tile)
    start = time.perf_counter()
    chunks.write_tile(
        path,
        tile,
        year,
        threshold,
        *arrays,
        chunks.tile_grid(tile).transform,
        provenance,
        overwrite=overwrite,
    )
    _verify_pair(path, tile, year, threshold, arrays)
    print(
        f"{tile} {year} t{threshold:g}: imported and verified both layers ({time.perf_counter() - start:.2f}s)"
    )


def _validate_source(src, source, tile):
    if src.crs != ws.MODIS_CRS or src.count != 1 or src.nodata != -1:
        raise ValueError(f"{source}: expected one MODIS band with nodata=-1")
    if chunks.offsets(ws.Grid(src.transform, src.shape)) != chunks.offsets(
        chunks.tile_grid(tile)
    ):
        raise ValueError(f"{source}: transform does not match tile")
    if not src.tags().get("product", "").startswith("MOD10A1F v61"):
        raise ValueError(f"{source}: expected MOD10A1F v61 provenance")


def _read_pair(fdl_path, tile):
    arrays, provenance = [], {}
    for kind in ("fdl", "lds"):
        source = fdl_path.with_name(kind + fdl_path.name[3:])
        with rasterio.open(source) as src:
            _validate_source(src, source, tile)
            arrays.append(src.read(1))
            provenance[kind] = {
                "source": source.name,
                "tags": src.tags(),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
    return arrays, provenance


def _verify_pair(path, tile, year, threshold, arrays):
    grid = chunks.tile_grid(tile)
    for kind, expected in zip(("FDL", "LDS"), arrays):
        actual = chunks.read_window(path, grid, [tile], year, threshold, kind)
        if not np.array_equal(actual, expected):
            raise ValueError(f"{tile} {year}: imported {kind} differs from source")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=FDL_STORE_DIR)
    sub = ap.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import")
    imp.add_argument("--overwrite", action="store_true")
    exp = sub.add_parser("export")
    exp.add_argument("--tile", required=True)
    exp.add_argument("--year", required=True, type=int)
    exp.add_argument("--threshold", type=float, default=10)
    exp.add_argument("--kind", choices=["FDL", "LDS"], default="FDL")
    exp.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    path = chunks.database(args.store)
    if args.command == "import":
        files = sorted(args.store.glob("fdl_*.tif"))
        if not files:
            ap.error("No FDL GeoTIFFs found to import")
        for source in files:
            import_pair(path, source, overwrite=args.overwrite)
        print(
            f"Database: {path} ({path.stat().st_size:,} bytes); original GeoTIFFs retained"
        )
    else:
        if args.output.exists():
            ap.error("Output already exists; choose a new filename")
        chunks.export_tile(
            path, args.output, args.tile, args.year, args.threshold, args.kind
        )


if __name__ == "__main__":
    main()
