import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.utils.geo import InvalidAOI, point_to_bbox, validate_bbox, validate_point
from app.services.nisar_service import DemoProvider
from app.models.observation import Product

c = TestClient(app)


def test_point_validation():
    assert validate_point(23.8, 90.4) == (23.8, 90.4)
    with pytest.raises(InvalidAOI):
        validate_point(91, 0)
    with pytest.raises(InvalidAOI):
        validate_point(0, 181)


def test_bbox_validation():
    assert validate_bbox(0, 0, 1, 1)
    with pytest.raises(InvalidAOI):
        validate_bbox(1, 0, 0, 1)
    with pytest.raises(InvalidAOI):
        validate_bbox(0, 0, 10, 10)


def test_point_to_bbox_clamps():
    w, s, e, n = point_to_bbox(89.99, 179.99)
    assert n <= 90 and e <= 180


def test_demo_provider_never_invents():
    r = DemoProvider().search((0, 0, 1, 1), [Product.GUNW], None, None)
    assert r.count == 0 and r.origin == "demo"


def test_health_and_bad_search():
    assert c.get("/api/health").json()["status"] == "ok"
    assert c.get("/api/nisar/search?lat=999&lon=0").status_code == 422
    assert c.get("/api/nisar/search").status_code == 422


def test_coordinate_lookup():
    r = c.get("/api/locations/search", params={"q": "23.8103, 90.4125"}).json()
    assert r["results"][0]["lat"] == 23.8103
