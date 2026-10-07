"""Synthetic First-Day-Land (FDL) rasters for testing the PCA pipeline.

Each dummy year is built from one fixed "recurrent" melt pattern, then
perturbed the way real data is:
  * melt onset and melt duration shift from year to year,
  * clouds delay when land is first seen (FDL arrives late),
  * a few spurious early-melt pixels (like the dark specks in the paper),
  * scattered missing pixels, and NaN outside the watershed boundary.

Swap this module out for the real NSIDC retrieval + FDL extraction later;
everything downstream only expects a list of equally sized 2D arrays.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DummyStack:
    rasters: list[np.ndarray]  # one (H, W) FDL raster per year, NaN = no data
    years: list[int]
    true_pattern: np.ndarray   # (H, W) recurrent pattern, 0 = earliest melt, 1 = latest


def _smooth_terrain(shape: tuple[int, int], rng: np.random.Generator, n_peaks: int = 6) -> np.ndarray:
    """Sum of random Gaussian 'mountains', scaled to 0..1. Stands in for the melt-order field."""
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    z = np.zeros(shape)
    for _ in range(n_peaks):
        cy, cx = rng.uniform(0, h), rng.uniform(0, w)
        sy, sx = rng.uniform(0.1, 0.35) * h, rng.uniform(0.1, 0.35) * w
        z += rng.uniform(0.5, 1.0) * np.exp(-0.5 * (((y - cy) / sy) ** 2 + ((x - cx) / sx) ** 2))
    return (z - z.min()) / (z.max() - z.min())


def _watershed_mask(shape: tuple[int, int], rng: np.random.Generator) -> np.ndarray:
    """Irregular blob so the dummy 'watershed' isn't a rectangle."""
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    theta = np.arctan2(y - h / 2, x - w / 2)
    r = np.hypot((y - h / 2) / (h / 2), (x - w / 2) / (w / 2))
    edge = (0.85
            + 0.10 * np.sin(3 * theta + rng.uniform(0, 2 * np.pi))
            + 0.05 * np.sin(7 * theta + rng.uniform(0, 2 * np.pi)))
    return r <= edge


def make_dummy_fdl_stack(
    shape: tuple[int, int] = (80, 60),
    n_years: int = 17,
    start_year: int = 2000,
    seed: int = 0,
    mean_cloud_days: float = 4.0,
    spurious_frac: float = 0.002,
    missing_frac: float = 0.01,
    mask: np.ndarray | None = None,
) -> DummyStack:
    """mask: optional boolean (H, W) watershed mask, e.g. from watershed.rasterize_mask().
    If given, it sets the raster shape and replaces the random blob watershed."""
    if mask is not None:
        mask = np.asarray(mask, dtype=bool)
        shape = mask.shape
    rng = np.random.default_rng(seed)
    pattern = _smooth_terrain(shape, rng)
    inside = _watershed_mask(shape, rng) if mask is None else mask

    rasters = []
    for _ in range(n_years):
        onset = rng.normal(100, 10)                # DOY melt begins this year
        duration = max(rng.normal(90, 15), 30.0)   # days from first to last melt-out
        doy = onset + pattern * duration

        # Clouds hide the snow->land transition for a random number of days.
        cloud_delay = rng.geometric(1 / (1 + mean_cloud_days), size=shape) - 1
        doy = doy + cloud_delay

        spurious = rng.random(shape) < spurious_frac
        doy[spurious] = onset - rng.uniform(0, 20, spurious.sum())

        missing = rng.random(shape) < missing_frac
        doy[missing | ~inside] = np.nan
        rasters.append(np.round(doy))

    return DummyStack(
        rasters=rasters,
        years=list(range(start_year, start_year + n_years)),
        true_pattern=np.where(inside, pattern, np.nan),
    )
