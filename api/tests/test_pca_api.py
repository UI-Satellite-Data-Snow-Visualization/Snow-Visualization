"""POST /pca and its downloads, on a synthetic FDL store for South Fork Boise (HUC8 17050113).

Each stored year is one known melt pattern plus a year shift and noise, so PC1
should recover the pattern. A few pixels get "never melted" in one year and
must be dropped.
"""
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient

import config
from server import catalog, pca_service
from server.main import app
from snow import fdl as F
from snow import store
from snow import watershed as ws

SHED = "wbd_huc8_17050113"
YEARS = [2020, 2021, 2022]
N_BAD = 25

client = TestClient(app)


@pytest.fixture
def fake_store(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FDL_STORE_DIR", tmp_path)
    pca_service._cache.clear()
    shed = catalog.load_watershed(SHED)
    h, w = shed.grid.shape
    rows, cols = np.mgrid[0:h, 0:w]
    pattern = (rows / h + cols / w) / 2                    # 0 = earliest melt, 1 = latest
    rng = np.random.default_rng(0)
    bad = tuple(np.argwhere(shed.mask)[:N_BAD].T)          # inside the watershed
    for i, year in enumerate(YEARS):
        # Pattern spread inside the watershed is ~15 days (SD), against 2 days of noise per year.
        fdl = (100 + 200 * pattern + 8 * i + rng.normal(0, 2, (h, w))).round().astype(np.int16)
        if i == 1:
            fdl[bad] = F.NEVER_MELTED
        with rasterio.open(store.fdl_path(tmp_path, "h09v04", year), "w", driver="GTiff", height=h, width=w,
                           count=1, dtype="int16", crs=ws.MODIS_CRS, transform=shed.grid.transform,
                           nodata=F.NODATA) as dst:
            dst.write(fdl, 1)
    return shed, pattern


def post_pca(**kw):
    return client.post("/pca", json={"watershed_id": SHED, "years": YEARS, **kw})


def test_years(fake_store):
    body = client.get(f"/watersheds/{SHED}/years").json()
    assert body["tiles"] == ["h09v04"]
    assert body["years"] == YEARS


def test_pca_recovers_pattern(fake_store):
    shed, pattern = fake_store
    response = post_pca()
    assert response.status_code == 200
    body = response.json()
    assert body["pixels_in_watershed"] == 15_741
    assert body["pixels_used"] == 15_741 - N_BAD
    assert body["variance_explained"][0] > 0.8
    assert [s["year"] for s in body["year_stats"]] == YEARS
    # The preview is cropped to the watershed's pixels, so its edges sit within a pixel or so
    # (~0.006 degrees) of the boundary's extent: lon -115.937 to -114.636, lat 43.226 to 43.859.
    b = body["preview_bounds"]
    assert [b["west"], b["east"], b["south"], b["north"]] == pytest.approx(
        [-115.937, -114.636, 43.226, 43.859], abs=0.02)

    tif = client.get(body["geotiff_url"])
    assert tif.status_code == 200
    with rasterio.MemoryFile(tif.content) as mem, mem.open() as src:
        assert src.crs == ws.MODIS_CRS
        assert src.transform == shed.grid.transform
        assert src.tags()["years"] == "2020,2021,2022"
        pc1 = src.read(1)
    used = np.isfinite(pc1)
    assert used.sum() == body["pixels_used"]
    assert np.corrcoef(pc1[used], pattern[used])[0, 1] > 0.99   # higher PC1 = later melt


@pytest.mark.filterwarnings("ignore::rasterio.errors.NotGeoreferencedWarning")   # a plain PNG, no CRS
def test_preview_png(fake_store):
    png = client.get(post_pca().json()["preview_url"])
    assert png.headers["content-type"] == "image/png"
    with rasterio.MemoryFile(png.content) as mem, mem.open() as src:
        alpha = src.read(4)
    assert src.count == 4
    assert (alpha == 255).any() and (alpha == 0).any()     # watershed drawn, outside transparent


def test_scaling_changes_result(fake_store):
    cov, cor = post_pca().json(), post_pca(scaling="correlation").json()
    assert cov["result_id"] != cor["result_id"]
    assert cor["scaling"] == "correlation"


def test_missing_year_is_422(fake_store):
    response = client.post("/pca", json={"watershed_id": SHED, "years": [2020, 2019]})
    assert response.status_code == 422
    assert "2019" in response.json()["detail"]


def test_one_year_is_422(fake_store):
    assert client.post("/pca", json={"watershed_id": SHED, "years": [2020, 2020]}).status_code == 422


def test_unknown_watershed_is_404(fake_store):
    assert client.post("/pca", json={"watershed_id": "nope", "years": YEARS}).status_code == 404


def test_unknown_result_is_404():
    assert client.get("/pca/0000000000000000/pc1.tif").status_code == 404
