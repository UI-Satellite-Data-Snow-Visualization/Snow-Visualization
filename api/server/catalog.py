"""Find watershed boundaries in db/boundaries/ by id (the file name without .geojson)."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from fastapi import HTTPException

import config
from snow import watershed as ws

PIXEL_RULE = "pixel center inside boundary"


@dataclass(frozen=True)
class Watershed:
    id: str
    boundary: ws.Boundary
    grid: ws.Grid
    mask: np.ndarray     # True = pixel is in the watershed (PIXEL_RULE)
    tiles: list[str]


def load_boundary(watershed_id: str) -> ws.Boundary:
    path = (config.BOUNDARIES_DIR / f"{watershed_id}.geojson").resolve()
    # The id becomes a file name, so refuse anything that points outside db/boundaries/.
    if path.parent != config.BOUNDARIES_DIR.resolve() or not path.exists():
        raise HTTPException(status_code=404, detail=f"Watershed {watershed_id} not found")
    return ws.load_boundary(path)


@lru_cache(maxsize=64)
def load_watershed(watershed_id: str) -> Watershed:
    """Boundary plus its mask on the MODIS grid; cached because every PCA request needs it."""
    boundary = load_boundary(watershed_id)
    sinu = ws.to_sinusoidal(boundary.geometries)
    grid = ws.grid_for(sinu)
    mask = ws.rasterize_mask(sinu, grid)
    return Watershed(watershed_id, boundary, grid, mask, ws.modis_tiles(mask, grid))
