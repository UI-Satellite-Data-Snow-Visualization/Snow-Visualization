"""First day land (FDL) and last day snow (LDS) from daily MOD10A1F files.

Same algorithm as Woodruff's Starter_Code_FDL_LDS_MOD10A1F.py (left untouched
in the repo root): anchor on start_doy (91 = April 1), search forward for
pixels that are snow that day and backward for pixels that are clear. Changes:
- Reads the CGF_NDSI_Snow_Cover layer by name, as raw uint8, so fill and
  missing codes stay codes instead of becoming NaN (which gave FDL = 0).
- Reads only a window of the tile, so a watershed run doesn't load 2400 x 2400.
- Raises if the HDF grid metadata can't be parsed (no silent h00v00 fallback).
- Pixels with no snow/clear observation all season get NODATA, kept apart
  from 0 (never snow) and 365 (never melted).
Uses pyhdf to read the HDF4 files.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from affine import Affine

NEVER_SNOW = 0
NEVER_MELTED = 365          # author's TODO: 366 in leap years
NODATA = -1
LAYER = "CGF_NDSI_Snow_Cover"
MISSING_CODES = [200, 201, 211, 250, 254, 255]
INLAND_WATER, OCEAN = 237, 239


def doy_of(path: Path) -> int:
    m = re.search(r"\.A\d{4}(\d{3})\.", path.name)
    if not m:
        raise ValueError(f"No DOY in file name {path.name}")
    return int(m.group(1))


def tile_transform(path: Path) -> Affine:
    """Affine transform of a tile, from its StructMetadata.0 block."""
    from pyhdf.SD import SD, SDC

    meta = SD(str(path), SDC.READ).attributes()["StructMetadata.0"]
    ul = re.search(r"UpperLeftPointMtrs=\(([-\d.]+),([-\d.]+)\)", meta)
    lr = re.search(r"LowerRightMtrs=\(([-\d.]+),([-\d.]+)\)", meta)
    dim = re.search(r"XDim=(\d+)\s+YDim=(\d+)", meta)
    if not (ul and lr and dim):
        raise ValueError(f"Could not parse grid metadata in {path.name}")
    ulx, uly, lrx, lry = map(float, (*ul.groups(), *lr.groups()))
    cols, rows = map(int, dim.groups())
    return Affine((lrx - ulx) / cols, 0, ulx, 0, (lry - uly) / rows, uly)


def read_stack(files: list[Path], window: tuple[slice, slice]) -> tuple[np.ndarray, np.ndarray]:
    """Daily CGF NDSI for one window, as (doys, uint8 array of shape (T, H, W))."""
    from pyhdf.SD import SD, SDC

    files = sorted(files, key=doy_of)
    rows, cols = window
    arrays = []
    for f in files:
        sds = SD(str(f), SDC.READ).select(LAYER)
        arrays.append(np.asarray(sds[rows, cols], dtype=np.uint8))
    return np.array([doy_of(f) for f in files]), np.stack(arrays)


def fdl_lds(stack: np.ndarray, doys: np.ndarray, threshold: float = 10,
            start_doy: int = 91) -> tuple[np.ndarray, np.ndarray]:
    """FDL and LDS (int16 DOY rasters) for one season of daily NDSI codes."""
    num_days, height, width = stack.shape
    start = int(np.searchsorted(doys, start_doy))
    if start >= num_days or doys[start] != start_doy:
        start = int(np.argmin(np.abs(doys - start_doy)))
        print(f"  [notice] DOY {start_doy} missing; anchoring on DOY {doys[start]}")

    ocean = np.all(stack == OCEAN, axis=0)
    is_snow = (stack >= threshold) & (stack <= 100)
    is_clear = (stack < threshold) | (stack == INLAND_WATER)   # uint8, so >= 0 always holds
    is_missing = np.isin(stack, MISSING_CODES)

    fdl = np.full((height, width), NODATA, dtype=np.int16)
    lds = np.full((height, width), NODATA, dtype=np.int16)
    fdl[ocean] = lds[ocean] = 0

    # Start state; if missing on the start day, look forward, then backward.
    snow0, clear0, unresolved = is_snow[start].copy(), is_clear[start].copy(), is_missing[start].copy()
    for t in [*range(start + 1, num_days), *range(start - 1, -1, -1)]:
        if not unresolved.any():
            break
        s, c = unresolved & is_snow[t], unresolved & is_clear[t]
        snow0 |= s
        clear0 |= c
        unresolved &= ~(s | c)

    # Forward: snow at the start -> first clear day is FDL, last snow before it is LDS.
    fwd = snow0 & ~ocean
    last_snow = np.full((height, width), doys[start], dtype=np.int16)
    done = np.zeros((height, width), dtype=bool)
    for t in range(start, num_days):
        active = fwd & ~done
        if not active.any():
            break
        clear = active & is_clear[t]
        fdl[clear], lds[clear] = doys[t], last_snow[clear]
        done |= clear
        last_snow[active & is_snow[t]] = doys[t]
    fdl[fwd & ~done] = lds[fwd & ~done] = NEVER_MELTED

    # Backward: clear at the start -> most recent snow is LDS, the clear day after it FDL.
    back = clear0 & ~ocean
    first_clear = np.full((height, width), doys[start], dtype=np.int16)
    done = np.zeros((height, width), dtype=bool)
    for t in range(start, -1, -1):
        active = back & ~done
        if not active.any():
            break
        snow = active & is_snow[t]
        fdl[snow], lds[snow] = first_clear[snow], doys[t]
        done |= snow
        first_clear[active & is_clear[t]] = doys[t]
    fdl[back & ~done] = lds[back & ~done] = NEVER_SNOW

    return fdl, lds
