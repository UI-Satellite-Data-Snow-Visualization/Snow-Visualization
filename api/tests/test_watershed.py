"""Watershed boundary onto the MODIS grid (South Fork Boise, HUC8 17050113)."""
from pathlib import Path

from snow import watershed as ws

FIXTURE = Path(__file__).parent / "fixtures" / "wbd_huc8_17050113.geojson"


def mask(all_touched=False):
    sinu = ws.to_sinusoidal(ws.load_boundary(FIXTURE).geometries)
    grid = ws.grid_for(sinu)
    return ws.rasterize_mask(sinu, grid, all_touched=all_touched), grid


def test_pixel_counts_match_recorded_values():
    center, grid = mask()
    touched, _ = mask(all_touched=True)
    assert center.sum() == 15_741
    assert touched.sum() == 16_422
    area_km2 = center.sum() * ws.PIXEL_SIZE_500M ** 2 / 1e6
    assert abs(area_km2 - 3_384) / 3_384 < 0.01     # WBD lists 3,384 km²; sinusoidal preserves area


def test_single_tile():
    center, grid = mask()
    assert ws.modis_tiles(center, grid) == ["h09v04"]
