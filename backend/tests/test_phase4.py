import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.algorithms.deformation import (
    build_quality_mask,
    chain_time_series,
    confidence_from,
    extract_change_zones,
    parse_granule_dates,
    phase_to_los_mm,
    reference_to_stable_area,
    summarize,
)


def test_phase_to_los_mm_and_sign():
    wavelength = 0.24
    expected = wavelength / (4 * np.pi) * 1000
    assert np.isclose(phase_to_los_mm(np.array([1.0]), wavelength)[0], expected)
    assert np.isclose(phase_to_los_mm(np.array([1.0]), wavelength, -1)[0], -expected)


def test_quality_mask_and_reference():
    quality = build_quality_mask(np.array([[.8, .4], [.9, .9]]), np.array([[1, 1], [0, 2]]), .5)
    assert quality.tolist() == [[True, False], [False, False]]
    shifted, reference = reference_to_stable_area(np.array([[11., 12.]]), np.array([[True, True]]))
    assert reference == 11.5 and np.allclose(shifted, [[-.5, .5]])


def test_summarize_and_zones():
    values = np.array([[0., 12.], [0., 15.]])
    mask = np.array([[True, True], [True, False]])
    result = summarize(values, mask, 0.01, 10)
    assert result.valid_fraction == .75 and result.affected_area_km2 == .01
    zones = extract_change_zones(values, mask, 10, (0, 100, 0, 200, 0, -100), 32646, .01)
    assert len(zones["features"]) == 1
    assert zones["features"][0]["properties"]["area_km2"] == .01


def test_chain_requires_temporal_contiguity_and_metadata():
    first = "NISAR_L2_PR_GUNW_023_040_A_014_024_4000_SH_20260616T230456_20260616T230531_20260628T230456_20260628T230530_P05023_N_F_J_001"
    second = first.replace("20260616T230456_20260616T230531_20260628T230456_20260628T230530",
                           "20260628T230456_20260628T230530_20260710T230456_20260710T230530")
    gap = first.replace("20260616T230456_20260616T230531_20260628T230456_20260628T230530",
                        "20260720T230456_20260720T230530_20260801T230456_20260801T230530")
    assert parse_granule_dates(first)["track"] == "040"
    assert [len(s) for s in chain_time_series([{"granule_id": first}, {"granule_id": second}, {"granule_id": gap}])] == [2, 1]


def test_confidence_and_insufficient_summary():
    assert confidence_from(.05, .9)[0] == "insufficient"
    assert confidence_from(.6, .8)[0] == "high"
    result = summarize(np.full((2, 2), np.nan), np.zeros((2, 2), dtype=bool), .01, 10)
    assert result.status == "insufficient" and result.mean is None


def test_api_rejects_bad_bbox_and_returns_insufficient_timeseries(monkeypatch):
    client = TestClient(app)
    response = client.post("/api/analysis", json={"bbox": [1, 2, 1, 3], "change_type": "ground", "granule_ids": []})
    assert response.status_code == 422

    monkeypatch.setattr(
        "app.api.routes.analysis.run_ground_analysis",
        lambda bbox, granule_ids: ("test-analysis", {"status": "insufficient", "zones": {"type": "FeatureCollection", "features": []}}),
    )
    monkeypatch.setattr("app.api.routes.analysis.get_result", lambda analysis_id: {"status": "insufficient"})
    response = client.post("/api/analysis", json={"lat": 1, "lon": 2, "change_type": "ground"})
    assert response.status_code == 200
    response = client.get("/api/analysis/test-analysis/timeseries")
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient"
