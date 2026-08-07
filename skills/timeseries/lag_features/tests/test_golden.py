"""Golden cases for timeseries.lag_features (v2.3 Wave A)."""

from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_lag1_matches_closed_form() -> None:
    golden = GoldenCase(
        id="lag1_one_to_four.json",
        skill_id="timeseries.lag_features",
        skill_version="0.1.0",
        inputs={"values": [1.0, 2.0, 3.0, 4.0], "lags": [1]},
        expected_result={
            "lags": [1],
            "y": [2.0, 3.0, 4.0],
            "n_keep": 3,
            "n_original": 4,
            "max_lag": 1,
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-12,
        source="closed form: lag-1 aligns y[k] with values[k-1]",
        justification="Direct indexing of an integer sequence; no SciPy involved.",
    )
    out = implementation.execute(golden.inputs)
    actual = {
        "lags": out["result"]["lags"],
        "y": out["result"]["y"],
        "n_keep": out["result"]["n_keep"],
        "n_original": out["result"]["n_original"],
        "max_lag": out["result"]["max_lag"],
        "backend": out["result"]["backend"],
        "converged": out["result"]["converged"],
    }
    assert_matches_golden(actual, golden)
    assert out["result"]["columns"]["1"] == [1.0, 2.0, 3.0]


def test_multi_lag_alignment() -> None:
    """For values=[10,20,30,40,50] and lags=[1,2]:
    y = [30,40,50], column 1 = [20,30,40], column 2 = [10,20,30]."""
    out = implementation.execute(
        {"values": [10.0, 20.0, 30.0, 40.0, 50.0], "lags": [1, 2]}
    )
    assert out["result"]["n_keep"] == 3
    assert out["result"]["max_lag"] == 2
    assert out["result"]["y"] == [30.0, 40.0, 50.0]
    assert out["result"]["columns"]["1"] == [20.0, 30.0, 40.0]
    assert out["result"]["columns"]["2"] == [10.0, 20.0, 30.0]