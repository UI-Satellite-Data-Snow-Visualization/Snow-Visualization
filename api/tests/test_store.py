"""snow/store.py: reading watershed windows out of stored FDL tiles, including across two tiles."""
import numpy as np
import pytest
import rasterio
from affine import Affine

from snow import fdl as F
from snow import store
from snow import watershed as ws

PX = ws.PIXEL_SIZE_500M


def write_fdl(path, array, transform):
    with rasterio.open(path, "w", driver="GTiff", height=array.shape[0], width=array.shape[1], count=1,
                       dtype="int16", crs=ws.MODIS_CRS, transform=transform, nodata=F.NODATA) as dst:
        dst.write(array.astype("int16"), 1)


def test_read_across_two_tiles(tmp_path):
    # A 10 x 12 watershed grid whose left 5 columns sit in one stored file and the rest in another.
    grid = ws.Grid(Affine(PX, 0, -10_000_000.0, 0, -PX, 5_000_000.0), (10, 12))
    truth = np.arange(120, dtype=np.int16).reshape(10, 12) + 100
    left = Affine(PX, 0, grid.transform.c - 3 * PX, 0, -PX, grid.transform.f + 2 * PX)   # starts 3 cols, 2 rows earlier
    write_fdl(store.fdl_path(tmp_path, "h01v01", 2020), np.pad(truth[:, :5], ((2, 4), (3, 0))), left)
    write_fdl(store.fdl_path(tmp_path, "h02v01", 2020), truth[:, 5:], grid.transform @ Affine.translation(5, 0))

    got = store.read_fdl(tmp_path, grid, ["h01v01", "h02v01"], 2020)
    np.testing.assert_array_equal(got, truth)


def test_uncovered_cells_are_nodata(tmp_path):
    grid = ws.Grid(Affine(PX, 0, 0.0, 0, -PX, 0.0), (4, 4))
    write_fdl(store.fdl_path(tmp_path, "h18v08", 2021), np.full((4, 2), 120), grid.transform)
    got = store.read_fdl(tmp_path, grid, ["h18v08"], 2021)
    assert (got[:, :2] == 120).all() and (got[:, 2:] == F.NODATA).all()


def test_stored_years_needs_every_tile(tmp_path):
    t = Affine(PX, 0, 0.0, 0, -PX, 0.0)
    for tile, year in [("h09v04", 2020), ("h10v04", 2020), ("h09v04", 2021)]:
        write_fdl(store.fdl_path(tmp_path, tile, year), np.zeros((2, 2)), t)
    write_fdl(tmp_path / "fdl_h09v04_2022_t20.tif", np.zeros((2, 2)), t)   # other threshold
    assert store.stored_years(tmp_path, ["h09v04", "h10v04"]) == [2020]
    assert store.stored_years(tmp_path, ["h09v04"]) == [2020, 2021]
    assert store.stored_years(tmp_path, ["h09v04"], threshold=20) == [2022]


def test_misaligned_file_is_refused(tmp_path):
    grid = ws.Grid(Affine(PX, 0, 0.0, 0, -PX, 0.0), (4, 4))
    write_fdl(store.fdl_path(tmp_path, "h18v08", 2020), np.zeros((4, 4)), grid.transform @ Affine.translation(0.5, 0))
    with pytest.raises(ValueError, match="not aligned"):
        store.read_fdl(tmp_path, grid, ["h18v08"], 2020)


def test_missing_file_is_an_error(tmp_path):
    grid = ws.Grid(Affine(PX, 0, 0.0, 0, -PX, 0.0), (4, 4))
    with pytest.raises(FileNotFoundError):
        store.read_fdl(tmp_path, grid, ["h18v08"], 2020)
