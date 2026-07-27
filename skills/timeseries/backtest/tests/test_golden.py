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