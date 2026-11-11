"""VIIRS support: product registry, HDF5 reading, precompute, watershed grid and API.

VIIRS gap-filled snow (VNP10A1F / VJ110A1F v2) shares the MODIS sinusoidal tiles
but has 3000 x 3000 pixels per tile (~371 m) in HDF-EOS5 files. These tests use
synthetic files and stores; real VNP10A1F downloads are checked with
`python -m jobs.inspect_granule --fetch viirs`.
"""
from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient

import config
from server import catalog, pca_service
from server.main import app
from snow import chunks, granules, products
from snow import fdl as F
from snow import watershed as ws

SHED = "wbd_huc8_17050113"
VIIRS = products.VIIRS_NPP
client = TestClient(app)


def struct_metadata(tile, pixels):
    """A StructMetadata.0 grid block like the real VNP10A1 v002 files carry."""
    grid = chunks.tile_grid(tile, products.get("viirs").grid if pixels == 3000 else chunks.MODIS)
    t = grid.transform
    lrx, lry = t @ (pixels, pixels)
    return (f'GROUP=GridStructure\n\tGROUP=GRID_1\n\t\tGridName="VIIRS_Grid_IMG_2D"\n'
            f'\t\tXDim={pixels}\n\t\tYDim={pixels}\n'
            f'\t\tUpperLeftPointMtrs=({t.c:.6f},{t.f:.6f})\n\t\tLowerRightMtrs=({lrx:.6f},{lry:.6f})\n'
            f'\t\tProjection=HE5_GCTP_SNSOID\n\tEND_GROUP=GRID_1\nEND_GROUP=GridStructure\n')


def write_h5(path, values, tile="h09v04", layer="CGF_NDSI_Snow_Cover", dtype="uint8"):
    h5py = pytest.importorskip("h5py")
    with h5py.File(path, "w") as f:
        meta = struct_metadata(tile, values.shape[0]).encode()
        f.create_dataset("HDFEOS INFORMATION/StructMetadata.0", data=np.bytes_(meta))
        fields = f.create_group("HDFEOS/GRIDS/VIIRS_Grid_IMG_2D/Data Fields")
        fields.create_dataset(layer, data=values.astype(dtype), compression="gzip")
        fields.create_dataset("Basic_QA", data=np.zeros(values.shape, "uint8"), compression="gzip")
    return path


def test_registry():
    assert products.get("viirs") is VIIRS
    assert products.get("VNP10A1F.002") is VIIRS and products.get("vj110a1f").first_year == 2018
    assert products.MODIS.grid == chunks.MODIS                       # unchanged storage key/grid
    assert VIIRS.pixel_size == pytest.approx(370.650173, abs=1e-5)
    assert VIIRS.granule_pattern(2024, "h09v04") == "VNP10A1F.A2024*.h09v04.002.*"
    assert products.for_file("VNP10A1F.A2024106.h09v04.002.2024107080550.h5") is VIIRS
    with pytest.raises(ValueError, match="Unknown product"):
        products.get("landsat")


def test_read_hdf5_layer(tmp_path):
    truth = np.zeros((3000, 3000), "uint8")
    truth[:10, :10] = 80
    truth[-5:, -5:] = 250                                            # cloud stays a code
    path = write_h5(tmp_path / "VNP10A1F.A2024106.h09v04.002.2024107080550.h5", truth)
    transform, data = granules.read_layer(path, VIIRS.layer)
    assert data.dtype == np.uint8 and data.shape == (3000, 3000)
    np.testing.assert_array_equal(data, truth)
    assert chunks.offsets(ws.Grid(transform, data.shape), VIIRS.grid) == \
        chunks.offsets(chunks.tile_grid("h09v04", VIIRS.grid), VIIRS.grid)
    _, window = granules.read_layer(path, VIIRS.layer, (slice(0, 4), slice(8, 12)))
    np.testing.assert_array_equal(window, truth[:4, 8:12])


def test_hdf5_errors(tmp_path):
    values = np.zeros((3000, 3000))
    signed = write_h5(tmp_path / "a.h5", values, dtype="int16")
    with pytest.raises(ValueError, match="not uint8"):
        granules.read_layer(signed, VIIRS.layer)
    with pytest.raises(KeyError, match="Basic_QA"):                 # lists the layers it found
        granules.read_layer(signed, "NDSI_Snow_Cover")
    with pytest.raises(ValueError, match="unsupported"):
        granules.read_layer(tmp_path / "x.nc", VIIRS.layer)


def test_precompute_reads_and_stores_viirs(tmp_path, monkeypatch):
    from jobs import precompute_fdl as job
    days = {1: np.full((3000, 3000), 60, "uint8"), 2: np.zeros((3000, 3000), "uint8")}
    days[2][:200, :200] = 211                                        # night: unknown, not land
    names = {d: f"VNP10A1F.A2021{d:03d}.h09v04.002.2021999999999.h5" for d in days}
    monkeypatch.setattr(job, "find_granules", lambda *a: {d: {"name": n} for d, n in names.items()})
    monkeypatch.setattr(job, "fetch", lambda g, dest: write_h5(dest, days[F.doy_of(dest)]))
    writes = []
    monkeypatch.setattr(job.chunks, "write_tile", lambda *a, **kw: writes.append((a, kw)))
    args = SimpleNamespace(last_doy=2, start_doy=1, tmp=tmp_path, workers=2, out=tmp_path,
                           overwrite=False, product=VIIRS)
    job.process_tile_year("h09v04", 2021, args, [10])
    (a, kw), = writes
    fdl, provenance = a[4], a[7]
    assert kw["product_grid"] == VIIRS.grid
    assert fdl.shape == (3000, 3000)
    assert (fdl[200:, 200:] == 2).all()                              # melted on day 2
    assert (fdl[:200, :200] == F.NEVER_MELTED).all()                 # never seen clear
    assert provenance["product_key"] == "VNP10A1F.002"
    assert "VNP10A1F v2" in provenance["product"]


def test_read_cgf_rejects_modis_sized_file_as_viirs(tmp_path):
    from jobs import precompute_fdl as job
    path = write_h5(tmp_path / "VNP10A1F.A2021001.h09v04.002.1.h5", np.zeros((2400, 2400)))
    with pytest.raises(ValueError, match="expected"):
        job.read_cgf(path, VIIRS)


def test_viirs_watershed_grid():
    modis = catalog.load_watershed(SHED)
    viirs = catalog.load_watershed(SHED, VIIRS.key)
    assert viirs.grid.transform.a == pytest.approx(VIIRS.pixel_size)
    chunks.offsets(viirs.grid, VIIRS.grid)                            # on the VIIRS lattice
    assert viirs.tiles == modis.tiles == ["h09v04"]
    ratio = (products.MODIS.pixel_size / VIIRS.pixel_size) ** 2      # 1.5625 pixels per MODIS pixel
    assert viirs.mask.sum() == pytest.approx(modis.mask.sum() * ratio, rel=0.02)


@pytest.fixture
def viirs_store(tmp_path, monkeypatch):
    """Three synthetic VIIRS years in SQLite; no MODIS data at all."""
    monkeypatch.setattr(config, "FDL_STORE_DIR", tmp_path)
    pca_service._cache.clear()
    shed = catalog.load_watershed(SHED, VIIRS.key)
    h, w = shed.grid.shape
    rows, cols = np.mgrid[0:h, 0:w]
    pattern = (rows / h + cols / w) / 2
    rng = np.random.default_rng(1)
    tile = chunks.tile_grid("h09v04", VIIRS.grid)
    sr, sc = chunks.offsets(shed.grid, VIIRS.grid)
    tr, tc = chunks.offsets(tile, VIIRS.grid)
    for i, year in enumerate([2020, 2021, 2022]):
        full = np.full((3000, 3000), F.NODATA, dtype=np.int16)
        full[sr - tr:sr - tr + h, sc - tc:sc - tc + w] = (
            100 + 200 * pattern + 8 * i + rng.normal(0, 2, (h, w))).round()
        chunks.write_tile(chunks.database(tmp_path), "h09v04", year, 10, full, full,
                          tile.transform, {"source": "synthetic VIIRS API test"},
                          product_grid=VIIRS.grid)
    return shed, pattern


def test_products_endpoint():
    body = client.get("/products").json()
    keys = [p["key"] for p in body]
    assert keys == ["MOD10A1F.061", "VNP10A1F.002", "VJ110A1F.002"]
    assert [p["default"] for p in body] == [True, False, False]


def test_years_are_per_product(viirs_store):
    viirs = client.get(f"/watersheds/{SHED}/years", params={"product": "viirs"}).json()
    assert viirs["product"] == "VNP10A1F.002" and viirs["years"] == [2020, 2021, 2022]
    assert client.get(f"/watersheds/{SHED}/years").json()["years"] == []      # MODIS not stored
    assert client.get(f"/watersheds/{SHED}/years", params={"product": "x"}).status_code == 422


def test_viirs_pca(viirs_store):
    shed, pattern = viirs_store
    response = client.post("/pca", json={"watershed_id": SHED, "years": [2020, 2021, 2022],
                                         "product": "viirs"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["product"] == "VNP10A1F.002" and body["pixel_size_m"] == pytest.approx(370.65, abs=0.01)
    assert body["pixels_in_watershed"] == int(shed.mask.sum()) == body["pixels_used"]
    assert body["variance_explained"][0] > 0.8
    tif = client.get(body["geotiff_url"])
    assert "VNP10A1F" in tif.headers["content-disposition"]
    with rasterio.MemoryFile(tif.content) as mem, mem.open() as src:
        assert src.transform == shed.grid.transform
        assert src.tags()["product_key"] == "VNP10A1F.002"
        pc1 = src.read(1)
    used = np.isfinite(pc1)
    assert np.corrcoef(pc1[used], pattern[used])[0, 1] > 0.99
    # The same request for MODIS is a different result and fails cleanly: no MODIS stored.
    modis = client.post("/pca", json={"watershed_id": SHED, "years": [2020, 2021]})
    assert modis.status_code == 422 and "MOD10A1F.061" in modis.json()["detail"]


def test_viirs_years_before_2012_are_explained(viirs_store):
    response = client.post("/pca", json={"watershed_id": SHED, "years": [2011, 2020], "product": "viirs"})
    assert response.status_code == 422
    assert "2012" in response.json()["detail"]
    assert client.post("/pca", json={"watershed_id": SHED, "years": [2020, 2021],
                                     "product": "landsat"}).status_code == 422


# --- Workbench (jobs.tui) and run_real with VIIRS -------------------------------

def write_viirs_season(folder, years=(2020, 2021)):
    """Three days per year on the full h09v04 VIIRS tile: snow, partial melt, clear.

    Day 2 melts a different checkerboard each year, so FDL is 2 or 3 and varies
    inside any watershed window.
    """
    r, c = np.indices((3000, 3000))
    for k, year in enumerate(years):
        melted = ((r // (7 + k) + c // (5 + 2 * k)) % 2) == 0
        days = {1: np.full((3000, 3000), 60), 2: np.where(melted, 0, 60), 3: np.zeros((3000, 3000))}
        for doy, values in days.items():
            write_h5(folder / f"VNP10A1F.A{year}{doy:03d}.h09v04.002.2021999999999.h5", values)


def test_workbench_synthetic_viirs_grid(tmp_path):
    import json
    from jobs.tui import Settings, process
    grid, mask, annual, pc1, out = process(Settings(product=VIIRS.key, years=(2020, 2021)), tmp_path)
    assert grid.transform.a == pytest.approx(VIIRS.pixel_size)
    assert mask.sum() == int(catalog.load_watershed(SHED, VIIRS.key).mask.sum())
    assert np.isfinite(pc1[mask]).all()
    meta = json.loads((out / "settings.json").read_text())
    assert meta["product"] == VIIRS.key and meta["sensor"] == "VIIRS Suomi NPP"
    with rasterio.open(out / "fdl_2020.tif") as src:
        assert src.transform == grid.transform


def test_workbench_real_viirs_files(tmp_path, monkeypatch):
    pytest.importorskip("h5py")
    from jobs import tui
    raw = tmp_path / "raw"
    raw.mkdir()
    write_viirs_season(raw)
    monkeypatch.setattr(tui, "RAW_DIR", raw)
    settings = tui.Settings(product="viirs", years=(2020, 2021), demo=False, start_doy=1, last_doy=3)
    grid, mask, annual, pc1, out = tui.process(settings, tmp_path / "out")
    for fdl, lds in annual.values():
        assert set(np.unique(fdl[mask])) == {2, 3}
        assert (lds[mask] < fdl[mask]).all()
    assert np.isfinite(pc1[mask]).all()
    with pytest.raises(ValueError, match="2012"):
        tui.process(tui.Settings(product="viirs", years=(2010, 2020)), tmp_path / "out")


def test_run_real_viirs(tmp_path, monkeypatch):
    pytest.importorskip("h5py")
    import sys
    from jobs import run_real
    raw = tmp_path / "raw"
    raw.mkdir()
    write_viirs_season(raw)
    monkeypatch.setattr(run_real, "HERE", tmp_path)
    monkeypatch.setattr(sys, "argv", ["run_real", "--product", "viirs", "--years", "2020", "2021",
                                      "--start-doy", "1", "--downloads", str(raw)])
    run_real.main()
    with rasterio.open(tmp_path / "output" / "pc1_17050113_VNP10A1F.tif") as src:
        assert src.transform.a == pytest.approx(VIIRS.pixel_size)
        assert np.isfinite(src.read(1)).sum() == int(catalog.load_watershed(SHED, VIIRS.key).mask.sum())
    assert (tmp_path / "output" / "real_pc1_VNP10A1F.png").exists()


def test_pixel_map_with_viirs_result(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from jobs.pixel_map import create_pixel_map
    from jobs.tui import Settings, process
    result = process(Settings(product=VIIRS.key, years=(2020, 2021)), tmp_path)
    fig, ax, click, details = create_pixel_map(
        result, recompute=lambda settings, **kw: process(settings, tmp_path, **kw))
    row, col = np.argwhere(result[1])[100]
    click(SimpleNamespace(inaxes=ax, xdata=float(col), ydata=float(row), button=1))
    assert f"SELECTED PIXEL: {row}, {col}" in details.get_text()
    assert "VIIRS sinusoidal" in details.get_text()
    fig._snow_threshold.set_val("40")
    fig._snow_apply_threshold(None)
    updated = fig._snow_result[0]
    assert updated[0] == result[0]                                  # still the VIIRS grid
    assert "Applied NDSI 40" in fig._snow_status.get_text()
    assert "VNP10A1F" in fig._suptitle.get_text()
    plt.close(fig)


def test_workbench_accepts_only_confirmed_archive_gaps(tmp_path, monkeypatch):
    """Real VIIRS 2024 has no files for DOY 192-197. The workbench must accept a gap NASA
    confirms, but still refuse days that exist at NASA and simply weren't downloaded."""
    pytest.importorskip("h5py")
    import json
    from jobs import tui
    from jobs.download import read_catalog, write_catalog
    raw = tmp_path / "raw"
    raw.mkdir()
    write_viirs_season(raw)                                  # days 1-3 on disk; day 4 never
    monkeypatch.setattr(tui, "RAW_DIR", raw)
    settings = tui.Settings(product="viirs", years=(2020, 2021), demo=False, start_doy=1, last_doy=4)
    with pytest.raises(ValueError, match="option 4"):         # no catalog saved yet
        tui.process(settings, tmp_path / "out")
    for year in (2020, 2021):                                 # NASA has day 4 -> unfinished download
        write_catalog(raw, VIIRS, "h09v04", year, 4, [1, 2, 3, 4])
    with pytest.raises(ValueError, match="not downloaded"):
        tui.process(settings, tmp_path / "out")
    for year in (2020, 2021):                                 # NASA lacks day 4 -> real gap
        write_catalog(raw, VIIRS, "h09v04", year, 4, [1, 2, 3])
    assert read_catalog(raw, VIIRS, "h09v04", 2020)["archive_gaps"] == [4]
    assert read_catalog(raw, products.MODIS, "h09v04", 2020) is None
    grid, mask, annual, pc1, out = tui.process(settings, tmp_path / "out")
    assert np.isfinite(pc1[mask]).all()
    assert json.loads((out / "settings.json").read_text())["archive_gaps"] == {"2020": [4], "2021": [4]}
    shorter = tui.Settings(product="viirs", years=(2020,), demo=False, start_doy=1, last_doy=5)
    with pytest.raises(ValueError, match="option 4"):         # catalog only searched to DOY 4
        tui.process(shorter, tmp_path / "out")
