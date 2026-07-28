"""Golden cases for timeseries.backtest (v2.3 Wave A)."""

from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_constant_series_naive_has_zero_errors() -> None:
    golden = GoldenCase(
        id="constant_series_naive.json",
        skill_id="timeseries.backtest",
        skill_version="0.1.0",
        inputs={"series": [7.0, 7.0, 7.0, 7.0], "steps_ahead": 1, "method": "naive"},
        expected_result={
            "method": "naive",
            "steps_ahead": 1,
            "period": None,
            "n_series": 4,
            "n_evaluations": 3,
            "mae": 0.0,
            "rmse": 0.0,
            "naive_baseline_mae": 0.0,
            "skill_score_vs_naive": 0.0,
            "errors": [0.0, 0.0, 0.0],
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-9,
        source="closed form: naive forecast of a constant series is exact",
        justification="All forecasted values equal the constant, errors are 0 by construction.",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_monotonic_series_naive_errors_match_closed_form() -> None:
    """For series=[1,2,3,4,5] with method=naive and steps_ahead=1:
    every error is actual - last = +1 (since each step increases by 1)."""
    out = implementation.execute(
        {"series": [1.0, 2.0, 3.0, 4.0, 5.0], "steps_ahead": 1, "method": "naive"}
    )
    assert out["result"]["errors"] == [1.0, 1.0, 1.0, 1.0]
    assert out["result"]["mae"] == 1.0
    assert out["result"]["rmse"] == 1.0
    # Naive baseline MAE here is also 1.0; skill score = 1 - 1/1 = 0
    assert abs(out["result"]["skill_score_vs_naive"]) < 1e-12


def test_mean_forecaster_backtest_mae_greater_than_zero_for_growth_series() -> None:
    out = implementation.execute(
        {"series": [1.0, 2.0, 3.0, 4.0, 5.0], "steps_ahead": 1, "method": "mean"}
    )
    assert out["result"]["mae"] > 0.0
    # Mean baseline should be worse than naive for monotonic series; skill <= 0
    assert out["result"]["skill_score_vs_naive"] <= 0.0


def test_seasonal_naive_on_exactly_periodic_series_is_perfect() -> None:
    """series=[10,20,30,40]x3 is exactly period-4; every one-step
    seasonal_naive forecast in the last 8 windows matches its held-out
    actual exactly, so mae=rmse=0 and skill vs. naive baseline is perfect."""
    series = [10.0, 20.0, 30.0, 40.0] * 3
    out = implementation.execute(
        {
            "series": series,
            "steps_ahead": 1,
            "method": "seasonal_naive",
            "period": 4,
            "n_evaluations": 8,
        }
    )["result"]
    assert out["n_series"] == 12
    assert out["n_evaluations"] == 8
    assert out["errors"] == [0.0] * 8
    assert out["mae"] == 0.0
    assert out["rmse"] == 0.0
    assert out["skill_score_vs_naive"] == 1.0


def test_mean_forecaster_single_evaluation_matches_closed_form() -> None:
    """series=[1,2,3,4,5,4,3,2,1], n_evaluations=1: the sole training
    window is the first 8 values (mean=3.0), held-out actual is the last
    value (1.0), so error=-2.0 exactly."""
    out = implementation.execute(
        {
            "series": [1.0, 2.0, 3.0, 4.0, 5.0, 4.0, 3.0, 2.0, 1.0],
            "steps_ahead": 1,
            "method": "mean",
            "n_evaluations": 1,
        }
    )["result"]
    assert out["errors"] == [-2.0]
    assert out["mae"] == 2.0
    assert out["rmse"] == 2.0
    assert out["skill_score_vs_naive"] == -1.0


def test_naive_forecaster_single_evaluation_matches_closed_form() -> None:
    """series=[1,1,1,1,5], n_evaluations=1: training window is [1,1,1,1]
    (naive forecast=1.0), held-out actual is 5.0, error=4.0 exactly --
    identical to the naive baseline itself, so skill score is exactly 0."""
    out = implementation.execute(
        {
            "series": [1.0, 1.0, 1.0, 1.0, 5.0],
            "steps_ahead": 1,
            "method": "naive",
            "n_evaluations": 1,
        }
    )["result"]
    assert out["errors"] == [4.0]
    assert out["mae"] == 4.0
    assert out["rmse"] == 4.0
    assert out["skill_score_vs_naive"] == 0.0
