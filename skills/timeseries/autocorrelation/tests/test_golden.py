"""Golden cases for timeseries.autocorrelation (v2.5.1)."""

from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_alternating_series_biased_acf_matches_hand_derived_values() -> None:
    """See references.md for the hand-derived c0=4, raw_k sums."""
    golden = GoldenCase(
        id="alternating.json",
        skill_id="timeseries.autocorrelation",
        skill_version="0.1.0",
        inputs={"series": [1.0, -1.0, 1.0, -1.0], "nlags": 3, "method": "biased"},
        expected_result={
            "acf": [1.0, -0.75, 0.5, -0.25],
            "n": 4,
            "nlags": 3,
            "method": "biased",
            "demean": True,
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-9,
        source="hand-derived from the sample-ACF definition",
        justification="c0=sum(y^2)=4; raw_1=-3, raw_2=2, raw_3=-1 give acf=[1,-.75,.5,-.25]",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_unbiased_estimator_hits_unit_magnitude_at_lag1() -> None:
    """raw_1=-3, n=4, k=1: r1 = raw*n/((n-1)*c0) = -3*4/(3*4) = -1.0 exactly."""
    out = implementation.execute(
        {"series": [1.0, -1.0, 1.0, -1.0], "nlags": 1, "method": "unbiased"}
    )
    assert out["result"]["acf"] == [1.0, -1.0]


def test_default_method_is_biased() -> None:
    out = implementation.execute({"series": [1.0, -1.0, 1.0, -1.0], "nlags": 3})
    assert out["result"]["method"] == "biased"
    assert out["result"]["acf"][1] == -0.75
