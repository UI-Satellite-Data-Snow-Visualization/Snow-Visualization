"""Convert a stack of yearly rasters into the M x N 'D matrix' and back.

Rows = pixels (M), columns = years (N), as in Woodruff & Qualls (2019), Sec. 3.1.
Works for any raster size and any number of years.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class PixelIndex:
    """Remembers which raster cells became matrix rows, so results can be mapped back."""
    shape: tuple[int, int]
    flat_idx: np.ndarray  # positions in the raveled raster, one per matrix row


def build_matrix(
    rasters: Sequence[np.ndarray],
    min_valid_frac: float = 1.0,
) -> tuple[np.ndarray, PixelIndex]:
    """Stack N rasters of shape (H, W) into D with shape (M, N).

    min_valid_frac: a pixel is kept only if it has valid (finite) values in at
        least this fraction of years. 1.0 = complete record required (safest).
        Below 1.0, remaining gaps are filled with that pixel's mean across years.
        That fill is a placeholder; the team should decide on the real policy.
    """
    if len(rasters) < 2:
        raise ValueError("Need at least 2 years of rasters.")
    shapes = {np.shape(r) for r in rasters}
    if len(shapes) != 1:
        raise ValueError(f"All rasters must share one shape; got {shapes}.")
    (h, w), = shapes

    stack = np.stack([np.asarray(r, dtype=float) for r in rasters], axis=-1)
    n_years = stack.shape[-1]
    flat = stack.reshape(-1, n_years)

    need = max(1, math.ceil(min_valid_frac * n_years))
    keep = np.isfinite(flat).sum(axis=1) >= need
    if not keep.any():
        raise ValueError("No pixels meet min_valid_frac; lower it or check the input.")

    D = flat[keep].copy()
    gaps = ~np.isfinite(D)
    if gaps.any():
        row_means = np.nanmean(D, axis=1)
        D[gaps] = np.take(row_means, np.nonzero(gaps)[0])

    return D, PixelIndex(shape=(h, w), flat_idx=np.flatnonzero(keep))


def to_raster(values: np.ndarray, index: PixelIndex, fill: float = np.nan) -> np.ndarray:
    """Put one value per matrix row back onto the (H, W) grid."""
    values = np.asarray(values)
    if values.shape != index.flat_idx.shape:
        raise ValueError(f"Expected {index.flat_idx.size} values, got {values.size}.")
    out = np.full(index.shape[0] * index.shape[1], fill, dtype=float)
    out[index.flat_idx] = values
    return out.reshape(index.shape)
