from fastapi.testclient import TestClient

from server.main import app

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
