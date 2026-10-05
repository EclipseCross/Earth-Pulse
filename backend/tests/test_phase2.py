import pytest
from app.core.config import settings
from app.models.change import ChangeType
from app.models.observation import DataOrigin, Observation, Product, SearchResult
from app.services import watch_service as ws
from app.services.nisar_service import EarthaccessProvider, resolve_short_names
from app.services.change_detection_service import _metric

CATALOG = [
    {"short_name": "A_GUNW", "title": "NISAR Beta Geocoded Unwrapped Interferogram Product (Version 1)"},
    {"short_name": "A_GCOV", "title": "NISAR Beta Geocoded Polarimetric Covariance Product (Version 1)"},
    {"short_name": "A_GOFF", "title": "NISAR Beta Geocoded Pixel Offsets (Version 1)"},
    {"short_name": "SMAP_SM", "title": "SMAP Soil Moisture"},           # not NISAR: must be ignored
    {"short_name": "A_SME2", "title": "NISAR Beta Soil Moisture (Version 1)"},
]


def test_resolver_matches_by_title_and_ignores_non_nisar():
    r = resolve_short_names(CATALOG)
    assert r["GUNW"] == ["A_GUNW"] and r["GOFF"] == ["A_GOFF"] and r["SME2"] == ["A_SME2"]
    assert r["GSLC"] == []  # absent in catalog -> empty, never guessed


def test_resolver_excludes_level_one_products_from_level_two_workflows():
    catalog = [
        {"short_name": "NISAR_L1_RUNW_PROVISIONAL_V1", "title": "NISAR Unwrapped Interferogram"},
        {"short_name": "NISAR_L1_RSLC_PROVISIONAL_V1", "title": "NISAR Single Look Complex"},
        {"short_name": "NISAR_L1_ROFF_PROVISIONAL_V1", "title": "NISAR Pixel Offsets"},
        {"short_name": "NISAR_L2_GUNW_PROVISIONAL_V1", "title": "NISAR Unwrapped Interferogram"},
    ]

    resolved = resolve_short_names(catalog)

    assert resolved["GUNW"] == ["NISAR_L2_GUNW_PROVISIONAL_V1"]
    assert resolved["GSLC"] == []
    assert resolved["GOFF"] == []


def test_live_search_accepts_granule_size_property(monkeypatch):
    class FakeGranule:
        size = 12.5

        def __getitem__(self, key):
            return {"umm": {"GranuleUR": "g1", "TemporalExtent": {"RangeDateTime": {}}}}[key]

        def data_links(self):
            return ["https://example.test/g1"]

    monkeypatch.setattr(EarthaccessProvider, "_login", lambda self: None)
    monkeypatch.setattr(EarthaccessProvider, "resolved", lambda self: {"GUNW": ["A_GUNW"]})
    fake_earthaccess = type("Earthaccess", (), {"search_data": staticmethod(lambda **_: [FakeGranule()])})
    monkeypatch.setitem(__import__("sys").modules, "earthaccess", fake_earthaccess)

    result = EarthaccessProvider().search((0, 0, 1, 1), [Product.GUNW], None, None)
    assert result.count == 1 and result.observations[0].size_mb == 12.5


class FakeProvider:
    def __init__(self):
        self.ids = ["g1", "g2"]

    def search(self, bbox, products, start, end):
        obs = [Observation(granule_id=i, product=Product.GUNW, acquisition_start="2026-08-01T00:00:00Z",
                           origin=DataOrigin.LIVE) for i in self.ids]
        return SearchResult(origin=DataOrigin.LIVE, bbox=bbox, products_searched=products, count=len(obs), observations=obs)


def test_watch_baseline_then_new(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "watch_db_path", str(tmp_path / "w.db"))
    wid = ws.create_watch(23.8, 90.4, ChangeType.GROUND)
    fp = FakeProvider()
    first = ws.check_watch(wid, fp)
    assert first["baseline_count"] == 2 and first["unread"] == 0 and first["new_observations"] == []
    fp.ids.append("g3")
    second = ws.check_watch(wid, fp)
    assert [n["granule_id"] for n in second["new_observations"]] == ["g3"] and second["unread"] == 1
    again = ws.check_watch(wid, fp)
    assert len(again["new_observations"]) == 1  # no duplicates
    ws.mark_read(wid)
    assert ws.get_watch(wid)["unread"] == 0


def test_watch_rejects_bad_coords(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "watch_db_path", str(tmp_path / "w.db"))
    with pytest.raises(ValueError):
        ws.create_watch(200, 0, ChangeType.AUTO)


def test_change_metrics_are_product_specific():
    import numpy as np
    assert _metric(Product.GCOV, np.array([[1.0, 2.0]]), np.array([[2.0, 2.0]]))[2] == "%"
    assert _metric(Product.SME2, np.array([[1.0, 2.0]]), np.array([[2.0, 4.0]]))[0] == "mean soil-moisture difference"
