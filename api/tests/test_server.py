import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from server.main import app
from server.routes.watersheds import get_watershed

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_watersheds():
    response = client.get("/watersheds")
    assert response.status_code == 200
    ids = [w["id"] for w in response.json()]
    assert "wbd_huc8_17050113" in ids
    for watershed in response.json():
        assert {"id", "name", "huc8", "area_km2"} <= watershed.keys()


def test_get_watershed():
    response = client.get("/watersheds/wbd_huc8_17050113")
    assert response.status_code == 200
    body = response.json()
    assert body["huc8"] == "17050113"
    assert body["geometries"]


def test_get_watershed_unknown_is_404():
    assert client.get("/watersheds/nope").status_code == 404


def test_get_watershed_rejects_paths_outside_boundaries():
    # Over HTTP an id can't contain "/", so call the route function directly with one
    # that points at a real file outside db/boundaries/ (the test fixture copy).
    with pytest.raises(HTTPException) as err:
        get_watershed("../../api/tests/fixtures/wbd_huc8_17050113")
    assert err.value.status_code == 404
