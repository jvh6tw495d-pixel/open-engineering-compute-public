"""Golden cases for timeseries.ar_yule_walker (v2.5.1)."""

from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_alternating_series_order1_matches_hand_derived_yule_walker() -> None:
    """See references.md: phi=-0.75, sample_variance=1.0, innovation=0.4375."""
    golden = GoldenCase(
        id="alternating_ar1.json",
        skill_id="timeseries.ar_yule_walker",
        skill_version="0.1.0",
        inputs={"series": [1.0, -1.0, 1.0, -1.0], "order": 1},
        expected_result={
            "ar_coefficients": [-0.75],
            "order_requested": 1,
            "order_reached": 1,
            "is_positive_definite": True,
            "innovation_variance": 0.4375,
            "sample_variance": 1.0,
            "acf_used": [1.0, -0.75],
            "n": 4,
            "demean": True,
            "method": "yule_walker_levinson_durbin",
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-9,
        source="hand-derived Yule-Walker AR(1) fit (see references.md)",
        justification="phi=r1/r0=-0.75; E1=1*(1-0.75^2)=0.4375; sample_variance=c0/n=1.0",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_higher_order_on_random_looking_series_stays_positive_definite() -> None:
    """Any series' biased ACF is guaranteed PSD; Levinson-Durbin must reach
    the full requested order regardless of what the series 'looks like'."""
    out = implementation.execute({"series": [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0], "order": 3})
    assert out["result"]["is_positive_definite"] is True
    assert out["result"]["order_reached"] == 3
    assert len(out["result"]["ar_coefficients"]) == 3
    assert out["result"]["innovation_variance"] >= 0.0
