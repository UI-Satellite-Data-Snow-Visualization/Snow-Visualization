"""Find watershed boundaries in db/boundaries/ by id (the file name without .geojson).

A watershed's pixel grid depends on the product: MODIS ~463 m, VIIRS ~371 m.
Each (watershed, product) pair gets its own mask on that product's native grid.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from fastapi import HTTPException

import config
from snow import products
from snow import watershed as ws

PIXEL_RULE = "pixel center inside boundary"


@dataclass(frozen=True)
class Watershed:
    id: str
    boundary: ws.Boundary
    grid: ws.Grid
    mask: np.ndarray     # True = pixel is in the watershed (PIXEL_RULE)
    tiles: list[str]
    product: str = products.DEFAULT.key


def load_boundary(watershed_id: str) -> ws.Boundary:
    path = (config.BOUNDARIES_DIR / f"{watershed_id}.geojson").resolve()
    # The id becomes a file name, so refuse anything that points outside db/boundaries/.
    if path.parent != config.BOUNDARIES_DIR.resolve() or not path.exists():
        raise HTTPException(status_code=404, detail=f"Watershed {watershed_id} not found")
    return ws.load_boundary(path)


def product_or_422(name: str) -> products.Product:
    try:
        return products.get(name)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err


@lru_cache(maxsize=64)
def load_watershed(watershed_id: str, product: str = products.DEFAULT.key) -> Watershed:
    """Boundary plus its mask on the product's grid; cached because every PCA request needs it."""
    prod = products.get(product)
    boundary = load_boundary(watershed_id)
    sinu = ws.to_sinusoidal(boundary.geometries)
    grid = ws.grid_for(sinu, pixel_size=prod.pixel_size)
    mask = ws.rasterize_mask(sinu, grid)
    return Watershed(watershed_id, boundary, grid, mask, ws.modis_tiles(mask, grid), prod.key)
