"""Read precomputed FDL rasters from the FDL store (written by jobs/precompute_fdl.py).

The store holds one GeoTIFF per tile, year and threshold. A watershed grid is cut
out of every stored tile it overlaps and the pieces are placed side by side, so a
watershed spanning several tiles needs no separate stitching step. Tiles and
watershed grids sit on the same global MODIS pixel lattice, so this is array
indexing only: nothing is resampled.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

from . import fdl as F
from .watershed import MODIS_CRS, Grid


def fdl_path(store_dir: str | Path, tile: str, year: int, threshold: float = 10) -> Path:
    return Path(store_dir) / f"fdl_{tile}_{year}_t{threshold:g}.tif"


def stored_years(store_dir: str | Path, tiles: list[str], threshold: float = 10) -> list[int]:
    """Years that have an FDL raster for every one of `tiles`."""
    pattern = re.compile(rf"fdl_(h\d\dv\d\d)_(\d{{4}})_t{re.escape(f'{threshold:g}')}\.tif")
    have: dict[int, set[str]] = {}
    for path in Path(store_dir).glob("fdl_*.tif"):
        m = pattern.fullmatch(path.name)
        if m:
            have.setdefault(int(m.group(2)), set()).add(m.group(1))
    return sorted(year for year, found in have.items() if set(tiles) <= found)


def read_fdl(store_dir: str | Path, grid: Grid, tiles: list[str], year: int,
             threshold: float = 10) -> np.ndarray:
    """int16 FDL for one year on `grid`; cells that no stored tile covers are F.NODATA."""
    out = np.full(grid.shape, F.NODATA, dtype=np.int16)
    h, w = grid.shape
    for tile in tiles:
        path = fdl_path(store_dir, tile, year, threshold)
        if not path.exists():
            raise FileNotFoundError(f"No stored FDL for {tile} {year} at threshold {threshold:g} ({path.name}).")
        with rasterio.open(path) as src:
            t = src.transform
            if src.crs != MODIS_CRS or not np.isclose(t.a, grid.transform.a) or not np.isclose(t.e, grid.transform.e):
                raise ValueError(f"{path.name} is not on the MODIS 500 m sinusoidal grid.")
            col = (grid.transform.c - t.c) / t.a
            row = (grid.transform.f - t.f) / t.e
            c0, r0 = round(col), round(row)
            if abs(col - c0) > 1e-3 or abs(row - r0) > 1e-3:
                raise ValueError(f"{path.name} is not aligned to the watershed grid's pixels.")
            # Overlap of the watershed grid with this tile, in tile rows/cols.
            tr0, tr1 = max(r0, 0), min(r0 + h, src.height)
            tc0, tc1 = max(c0, 0), min(c0 + w, src.width)
            if tr0 < tr1 and tc0 < tc1:
                out[tr0 - r0:tr1 - r0, tc0 - c0:tc1 - c0] = src.read(
                    1, window=Window(tc0, tr0, tc1 - tc0, tr1 - tr0))
    return out
