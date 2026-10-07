"""Put a watershed boundary onto the MODIS 500 m sinusoidal grid.

The boundary is reprojected into MODIS sinusoidal (the raster is never
resampled), then rasterized into a boolean mask on a grid snapped to the
global MODIS pixel lattice. That mask decides which pixels become rows of
the D matrix. Needs rasterio.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from affine import Affine
from rasterio.crs import CRS
from rasterio.features import rasterize
from rasterio.warp import transform_geom

# MODIS sinusoidal grid (MOD10A1 and the other 500 m land products).
MODIS_CRS = CRS.from_proj4("+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +R=6371007.181 +units=m +no_defs")
TILE_SIZE_M = 1111950.5197665233          # one hXXvYY tile, edge length
TILE_PIXELS_500M = 2400
PIXEL_SIZE_500M = TILE_SIZE_M / TILE_PIXELS_500M   # ~463.31 m
GRID_ORIGIN_X = -20015109.355798          # upper-left corner of tile h00v00
GRID_ORIGIN_Y = 10007554.677899


@dataclass(frozen=True)
class Boundary:
    geometries: list[dict]   # GeoJSON geometries, EPSG:4326
    properties: dict         # attributes of the first feature (e.g. huc8, name, areasqkm)


@dataclass(frozen=True)
class Grid:
    transform: Affine        # pixel -> MODIS sinusoidal meters
    shape: tuple[int, int]   # (rows, cols)
    crs: CRS = MODIS_CRS


def load_boundary(path: str | Path) -> Boundary:
    """Read a GeoJSON FeatureCollection (lon/lat) such as a WBD HUC export."""
    data = json.loads(Path(path).read_text())
    features = data["features"] if data.get("type") == "FeatureCollection" else [data]
    if not features:
        raise ValueError(f"No features in {path}.")
    return Boundary([f["geometry"] for f in features], dict(features[0].get("properties") or {}))


def to_sinusoidal(geometries: list[dict]) -> list[dict]:
    return [transform_geom("EPSG:4326", MODIS_CRS, g) for g in geometries]


def grid_for(sinu_geometries: list[dict], pad: int = 1) -> Grid:
    """Smallest grid, aligned to the global MODIS 500 m pixels, that covers the geometries."""
    xs, ys = [], []
    for g in sinu_geometries:
        for ring in _rings(g):
            xs.extend(p[0] for p in ring)
            ys.extend(p[1] for p in ring)
    px = PIXEL_SIZE_500M
    col0 = math.floor((min(xs) - GRID_ORIGIN_X) / px) - pad
    col1 = math.ceil((max(xs) - GRID_ORIGIN_X) / px) + pad
    row0 = math.floor((GRID_ORIGIN_Y - max(ys)) / px) - pad
    row1 = math.ceil((GRID_ORIGIN_Y - min(ys)) / px) + pad
    transform = Affine(px, 0, GRID_ORIGIN_X + col0 * px, 0, -px, GRID_ORIGIN_Y - row0 * px)
    return Grid(transform=transform, shape=(row1 - row0, col1 - col0))


def rasterize_mask(sinu_geometries: list[dict], grid: Grid, all_touched: bool = False) -> np.ndarray:
    """True where a pixel belongs to the watershed.

    all_touched=False: pixel center must fall inside (GDAL default).
    all_touched=True: any pixel the boundary touches is included.
    """
    return rasterize(
        [(g, 1) for g in sinu_geometries], out_shape=grid.shape, transform=grid.transform,
        fill=0, all_touched=all_touched, dtype="uint8",
    ).astype(bool)


def modis_tiles(mask: np.ndarray, grid: Grid) -> list[str]:
    """MODIS tile IDs (hXXvYY) containing at least one masked pixel center."""
    rows, cols = np.nonzero(mask)
    x, y = grid.transform * (cols + 0.5, rows + 0.5)
    h = np.floor((np.asarray(x) - GRID_ORIGIN_X) / TILE_SIZE_M).astype(int)
    v = np.floor((GRID_ORIGIN_Y - np.asarray(y)) / TILE_SIZE_M).astype(int)
    return sorted({f"h{a:02d}v{b:02d}" for a, b in zip(h, v)})


def write_geotiff(path: str | Path, array: np.ndarray, grid: Grid) -> None:
    """Write one float band in MODIS sinusoidal, NaN as nodata."""
    import rasterio

    if array.shape != grid.shape:
        raise ValueError(f"Array shape {array.shape} does not match grid {grid.shape}.")
    with rasterio.open(
        path, "w", driver="GTiff", height=grid.shape[0], width=grid.shape[1], count=1,
        dtype="float32", crs=grid.crs, transform=grid.transform, nodata=np.nan, compress="deflate",
    ) as dst:
        dst.write(array.astype("float32"), 1)


def _rings(geometry: dict):
    if geometry["type"] == "Polygon":
        yield from geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            yield from poly
    else:
        raise ValueError(f"Unsupported geometry type {geometry['type']}.")
