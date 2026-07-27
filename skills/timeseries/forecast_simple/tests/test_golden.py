"""Golden cases for timeseries.forecast_simple (v2.3 Wave A)."""

from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_naive_matches_closed_form() -> None:
    golden = GoldenCase(
        id="naive_last_two.json",
        skill_id="timeseries.forecast_simple",
        skill_version="0.1.0",
        inputs={"series": [1.0, 2.0, 3.0, 4.0], "steps_ahead": 2, "method": "naive"},
        expected_result={
            "method": "naive",
            "steps_ahead": 2,
            "n_series": 4,
            "period": None,
            "forecast": [4.0, 4.0],
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-12,
        source="closed form: naive forecast = last value repeated",
        justification="Definition of the naive forecaster; no fit involved.",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_mean_forecast_matches_average() -> None:
    out = implementation.execute(
        {"series": [1.0, 2.0, 3.0, 4.0], "steps_ahead": 3, "method": "mean"}
    )
    assert out["result"]["forecast"] == [2.5, 2.5, 2.5]


def test_seasonal_naive_repeats_last_period() -> None:
    """series=[1,2,3,4], period=2, steps_ahead=3:
    last period is [3,4]; forecast steps 1,2,3 = [3,4,3]."""
    out = implementation.execute(
        {"series": [1.0, 2.0, 3.0, 4.0], "steps_ahead": 3, "method": "seasonal_naive", "period": 2}
    )
    assert out["result"]["forecast"] == [3.0, 4.0, 3.0]