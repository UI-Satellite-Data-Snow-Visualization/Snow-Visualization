"""PC1 for one watershed from the FDL store: the steps of jobs/run_real.py, minus the daily files.

Results stay in memory, keyed by their inputs, so the GeoTIFF and preview
downloads reuse a PCA instead of rerunning it. The cache is per process: with
several uvicorn workers, each keeps its own.
"""
from __future__ import annotations

import hashlib
import json
import threading
import warnings
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np
from rasterio.enums import Resampling
from rasterio.errors import NotGeoreferencedWarning
from rasterio.io import MemoryFile
from rasterio.warp import calculate_default_transform, reproject, transform

import config
from server import catalog
from snow import PCAResult, build_matrix, run_pca, store, to_raster
from snow import fdl as F

# Blue ramp, dark = early melt, light = late (same as jobs/run_real.py).
RAMP = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"]
CACHE_SIZE = 32


class MissingYearsError(ValueError):
    pass


@dataclass(frozen=True)
class PCARun:
    result_id: str
    watershed: catalog.Watershed
    years: list[int]
    scaling: str
    threshold: float
    pc1: np.ndarray                  # on watershed.grid, NaN outside the pixels used
    result: PCAResult
    pixels_used: int
    preview_png: bytes               # PC1 in Web Mercator, transparent outside the watershed
    preview_bounds: dict[str, float]  # lon/lat edges of preview_png


_cache: OrderedDict[str, PCARun] = OrderedDict()
_lock = threading.Lock()


def result_id_for(watershed_id: str, years: list[int], scaling: str, threshold: float) -> str:
    key = json.dumps([watershed_id, sorted(years), scaling, threshold])
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def get(result_id: str) -> PCARun | None:
    with _lock:
        return _cache.get(result_id)


def run(watershed_id: str, years: list[int], scaling: str = "covariance", threshold: float = 10) -> PCARun:
    years = sorted(set(years))
    result_id = result_id_for(watershed_id, years, scaling, threshold)
    with _lock:
        if result_id in _cache:
            _cache.move_to_end(result_id)
            return _cache[result_id]

    shed = catalog.load_watershed(watershed_id)
    available = store.stored_years(config.FDL_STORE_DIR, shed.tiles, threshold)
    missing = [y for y in years if y not in available]
    if missing:
        raise MissingYearsError(
            f"No stored FDL at threshold {threshold:g} for {missing} (tiles {shed.tiles}). Available: {available}")

    # Same masking as run_real.py: outside the watershed, never snow, never melted and no data are dropped.
    rasters = []
    for year in years:
        fdl = store.read_fdl(config.FDL_STORE_DIR, shed.grid, shed.tiles, year, threshold)
        r = fdl.astype(float)
        r[~shed.mask | np.isin(fdl, [F.NEVER_SNOW, F.NEVER_MELTED, F.NODATA])] = np.nan
        rasters.append(r)
    D, index = build_matrix(rasters, min_valid_frac=1.0)
    result = run_pca(D, use_correlation=scaling == "correlation")
    pc1 = to_raster(result.pc(1), index)
    png, bounds = _preview(pc1, shed.grid)

    pca_run = PCARun(result_id, shed, years, scaling, threshold, pc1, result, D.shape[0], png, bounds)
    with _lock:
        _cache[result_id] = pca_run
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return pca_run


def geotiff_bytes(pca_run: PCARun) -> bytes:
    """PC1 as float32 GeoTIFF on the native MODIS grid, with provenance tags."""
    grid = pca_run.watershed.grid
    props = pca_run.watershed.boundary.properties
    with MemoryFile() as mem:
        with mem.open(driver="GTiff", height=grid.shape[0], width=grid.shape[1], count=1, dtype="float32",
                      crs=grid.crs, transform=grid.transform, nodata=np.nan, compress="deflate") as dst:
            dst.write(pca_run.pc1.astype("float32"), 1)
            dst.update_tags(
                layer="PC1 pixel scores (relative melt timing: lower = earlier)",
                product="MOD10A1F v61 (NSIDC), CGF_NDSI_Snow_Cover, FDL from db/fdl_store",
                watershed=f"{pca_run.watershed.id} ({props.get('name', '?')})",
                years=",".join(map(str, pca_run.years)),
                threshold=f"snow = NDSI >= {pca_run.threshold:g}",
                pca=f"{pca_run.scaling} matrix, uncentered scores (paper eq. 1)",
                pixel_rule=catalog.PIXEL_RULE,
                pixels_used=str(pca_run.pixels_used),
                variance_explained_pc1=f"{pca_run.result.explained_variance_ratio[0]:.4f}",
            )
        return mem.read()


def _preview(pc1: np.ndarray, grid) -> tuple[bytes, dict[str, float]]:
    """PC1 colored and reprojected to Web Mercator (nearest neighbor, display only)."""
    h, w = grid.shape
    left, top = grid.transform @ (0, 0)
    right, bottom = grid.transform @ (w, h)
    dst_t, dw, dh = calculate_default_transform(grid.crs, "EPSG:3857", w, h, left, bottom, right, top)
    shown = np.full((dh, dw), np.nan, dtype="float32")
    reproject(pc1.astype("float32"), shown, src_transform=grid.transform, src_crs=grid.crs, src_nodata=np.nan,
              dst_transform=dst_t, dst_crs="EPSG:3857", dst_nodata=np.nan, resampling=Resampling.nearest)

    # The sheared sinusoidal rectangle covers far more than the watershed in Web Mercator; crop to the data.
    rows, cols = np.nonzero(np.isfinite(shown))
    r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    shown = shown[r0:r1, c0:c1]
    dst_t = dst_t @ dst_t.translation(c0, r0)
    dh, dw = shown.shape

    valid = np.isfinite(shown)
    lo, hi = np.nanpercentile(shown, [2, 98])
    t = np.clip((np.nan_to_num(shown, nan=lo) - lo) / ((hi - lo) or 1), 0, 1)
    stops = np.linspace(0, 1, len(RAMP))
    rgb = [np.interp(t, stops, [int(c[i:i + 2], 16) for c in RAMP]) for i in (1, 3, 5)]
    rgba = np.stack([*rgb, np.where(valid, 255, 0)]).astype(np.uint8)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)   # a plain PNG; bounds travel separately
        with MemoryFile() as mem:
            with mem.open(driver="PNG", height=dh, width=dw, count=4, dtype="uint8") as dst:
                dst.write(rgba)
            png = mem.read()

    west, north = dst_t @ (0, 0)
    east, south = dst_t @ (dw, dh)
    lons, lats = transform("EPSG:3857", "EPSG:4326", [west, east], [south, north])
    return png, {"west": lons[0], "south": lats[0], "east": lons[1], "north": lats[1]}
