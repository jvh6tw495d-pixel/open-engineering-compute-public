"""Golden cases for statistics.bootstrap (v2.3 Wave A)."""

from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_point_estimate_matches_sample_mean() -> None:
    golden = GoldenCase(
        id="mean_one_to_ten.json",
        skill_id="statistics.bootstrap",
        skill_version="0.1.0",
        inputs={
            "samples": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "statistic": "mean",
            "confidence_level": 0.95,
            "n_resamples": 2000,
            "seed": 0,
        },
        expected_result={
            "statistic": "mean",
            "point_estimate": 5.5,
            "n": 10,
            "n_resamples": 2000,
            "confidence_level": 0.95,
            "backend": "numpy",
        },
        tolerance=1e-12,
        source="closed form: mean of [1..10] is 5.5",
        justification=(
            "The bootstrap CI is a nonparametric interval whose point estimate "
            "is the sample mean (5.5)."
        ),
    )
    out = implementation.execute(golden.inputs)
    actual = {
        "statistic": out["result"]["statistic"],
        "point_estimate": out["result"]["point_estimate"],
        "n": out["result"]["n"],
        "n_resamples": out["result"]["n_resamples"],
        "confidence_level": out["result"]["confidence_level"],
        "backend": out["result"]["backend"],
    }
    assert_matches_golden(actual, golden)


def test_ci_contains_point_estimate() -> None:
    out = implementation.execute(
        {
            "samples": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "confidence_level": 0.95,
            "n_resamples": 2000,
            "seed": 0,
        }
    )
    assert out["result"]["lower"] <= out["result"]["point_estimate"] <= out["result"]["upper"]


def test_deterministic_with_seed() -> None:
    inputs = {
        "samples": [1.0, 2.0, 3.0, 4.0, 5.0],
        "seed": 42,
        "n_resamples": 500,
    }
    a = implementation.execute(inputs)["result"]
    b = implementation.execute(inputs)["result"]
    assert a == b
