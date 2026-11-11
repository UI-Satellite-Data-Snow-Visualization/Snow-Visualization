import sqlite3

from affine import Affine
import numpy as np
import pytest
import rasterio

from snow import chunks, store
from snow import watershed as ws


def tile_values(offset=0):
    r, c = np.indices((2400, 2400))
    result = ((r + c + offset) % 366).astype('int16')
    result[199:202, 199:202] = -1
    return result


def write(path, tile='h09v04', year=2021, threshold=10, values=None, **kw):
    values = tile_values() if values is None else values
    chunks.write_tile(path, tile, year, threshold, values, values-1,
                      chunks.tile_grid(tile).transform, {'source': 'synthetic test'}, **kw)
    return values


def test_roundtrip_and_export(tmp_path):
    path = chunks.database(tmp_path)
    truth = write(path)
    grid = chunks.tile_grid('h09v04')
    np.testing.assert_array_equal(chunks.read_window(path, grid, ['h09v04'], 2021), truth)
    window = ws.Grid(grid.transform @ Affine.translation(195, 195), (212, 215))
    np.testing.assert_array_equal(store.read_fdl(tmp_path, window, ['h09v04'], 2021), truth[195:407, 195:410])
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT count(*) FROM chunks').fetchone()[0] == 288
        assert conn.execute('SELECT min(chunk_col),min(chunk_row) FROM chunks').fetchone() == (108, 48)
    dest = tmp_path / 'export.tif'
    chunks.export_tile(path, dest, 'h09v04', 2021, kind='LDS')
    with rasterio.open(dest) as src:
        np.testing.assert_array_equal(src.read(1), truth-1)
        assert src.transform == grid.transform and src.crs == ws.MODIS_CRS
        assert src.nodata == -1 and 'synthetic test' in src.tags()['provenance']


def test_cross_tile_year_threshold_and_missing(tmp_path):
    path = chunks.database(tmp_path)
    left = write(path)
    right = write(path, 'h10v04', values=tile_values(30))
    write(path, year=2022, threshold=20)
    assert store.stored_years(tmp_path, ['h09v04', 'h10v04']) == [2021]
    assert store.stored_years(tmp_path, ['h09v04'], 20) == [2022]
    grid = ws.Grid(chunks.tile_grid('h09v04').transform @ Affine.translation(2397, 198), (5, 8))
    expected = np.concatenate([left[198:203, -3:], right[198:203, :5]], axis=1)
    np.testing.assert_array_equal(store.read_fdl(tmp_path, grid, ['h09v04', 'h10v04'], 2021), expected)
    with pytest.raises(FileNotFoundError):
        store.read_fdl(tmp_path, grid, ['h09v04', 'h10v04'], 2022, 20)
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM chunks WHERE chunk_row=48 AND chunk_col=119 AND kind='FDL'")
    with pytest.raises(ValueError, match='Incomplete'):
        store.read_fdl(tmp_path, grid, ['h09v04', 'h10v04'], 2021)


def test_validation_and_atomic_overwrite(tmp_path, monkeypatch):
    path = chunks.database(tmp_path)
    truth = write(path)
    with pytest.raises(FileExistsError):
        write(path)
    with pytest.raises(ValueError, match='2400'):
        write(path, values=np.zeros((200, 200), dtype='int16'))
    grid = chunks.tile_grid('h09v04')
    with pytest.raises(ValueError, match='aligned'):
        chunks.read_window(path, ws.Grid(grid.transform @ Affine.translation(.5, 0), (5, 5)), ['h09v04'], 2021)
    compress = chunks.zlib.compress
    calls = 0
    def fail_midway(data):
        nonlocal calls
        calls += 1
        if calls == 5:
            raise RuntimeError('interrupted')
        return compress(data)
    monkeypatch.setattr(chunks.zlib, 'compress', fail_midway)
    with pytest.raises(RuntimeError):
        write(path, values=tile_values(10), overwrite=True)
    np.testing.assert_array_equal(chunks.read_window(path, grid, ['h09v04'], 2021), truth)


def test_precompute_reuses_daily_stack_for_thresholds(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from jobs import precompute_fdl as job
    from snow import products
    monkeypatch.setattr(job, 'find_granules', lambda *args: {
        1: {'name': 'one.hdf'}, 2: {'name': 'two.hdf'}})
    monkeypatch.setattr(job, 'fetch', lambda *args: None)
    reads = []
    def read(path, product):
        reads.append(path.name)
        return chunks.tile_grid('h09v04').transform, np.full((2, 2), 15 if path.name == 'one.hdf' else 0, dtype='uint8')
    monkeypatch.setattr(job, 'read_cgf', read)
    writes = []
    monkeypatch.setattr(job.chunks, 'write_tile', lambda *args, **kw: writes.append(args))
    args = SimpleNamespace(last_doy=2, start_doy=1, tmp=tmp_path, workers=1, out=tmp_path, overwrite=False,
                           product=products.MODIS)
    job.process_tile_year('h09v04', 2021, args, [10, 20])
    assert sorted(reads) == ['one.hdf', 'two.hdf']
    assert [w[3] for w in writes] == [10, 20]
    assert (writes[0][4] == 2).all()   # first day land at threshold 10
    assert (writes[1][4] == 0).all()   # never snow at threshold 20


def test_product_dimensions_and_isolation(tmp_path):
    path = chunks.database(tmp_path)
    viirs = chunks.ProductGrid('VNP10A1F.002', ws.TILE_SIZE_M / 3000, 3000,
                               ws.GRID_ORIGIN_X, ws.GRID_ORIGIN_Y, ws.MODIS_CRS)
    write(path)
    truth = np.full((3000, 3000), 123, dtype=np.int16)
    truth[-200:, -200:] = 234
    grid = chunks.tile_grid('h09v04', viirs)
    chunks.write_tile(path, 'h09v04', 2021, 10, truth, truth, grid.transform,
                      {'source': 'synthetic VIIRS grid'}, product_grid=viirs)
    np.testing.assert_array_equal(chunks.read_window(path, grid, ['h09v04'], 2021,
                                                    product=viirs.product), truth)
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT count(*) FROM chunks WHERE product=?', (viirs.product,)).fetchone()[0] == 450
    dest = tmp_path / 'viirs.tif'
    chunks.export_tile(path, dest, 'h09v04', 2021, product=viirs.product)
    with rasterio.open(dest) as src:
        assert src.shape == (3000, 3000)
        assert src.transform == grid.transform
        np.testing.assert_array_equal(src.read(1), truth)
    with pytest.raises(ValueError, match='pixel lattice'):
        chunks.read_window(path, grid, ['h09v04'], 2021)
    conflicting = chunks.ProductGrid(viirs.product, ws.PIXEL_SIZE_500M, ws.TILE_PIXELS_500M,
                                     ws.GRID_ORIGIN_X, ws.GRID_ORIGIN_Y, ws.MODIS_CRS)
    with pytest.raises(ValueError, match='conflicts'):
        chunks.write_tile(path, 'h09v04', 2022, 10, tile_values(), tile_values(),
                          chunks.tile_grid('h09v04').transform, {}, product_grid=conflicting)
