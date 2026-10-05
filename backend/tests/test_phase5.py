import numpy as np

from app.algorithms.backscatter import (
    multilook_mean,
    power_to_db,
    robust_z_score,
    summarize_backscatter,
)


def test_power_to_db_and_multilook():
    assert np.allclose(power_to_db(np.array([1.0, 10.0])), [0.0, 10.0])
    assert np.allclose(multilook_mean(np.arange(16).reshape(4, 4), 2), [[2.5, 4.5], [10.5, 12.5]])


def test_robust_rule_and_summary():
    change = np.array([[0.0, 4.0], [-4.0, 0.0]])
    z = robust_z_score(change, np.ones((2, 2), dtype=bool))
    assert np.isfinite(z).all()
    result = summarize_backscatter(
        np.zeros((2, 2)), change, np.ones((2, 2), dtype=bool), .01, 3.0,
    )
    assert result.mean_db_change == 0.0
    assert result.affected_area_km2 == .02


def test_insufficient_backscatter_has_no_numbers():
    result = summarize_backscatter(
        np.ones((2, 2)), np.ones((2, 2)), np.zeros((2, 2), dtype=bool), .01, 3.0,
    )
    assert result.status == "insufficient"
    assert result.mean_db_change is None
    assert result.message == "Insufficient data for reliable analysis."
