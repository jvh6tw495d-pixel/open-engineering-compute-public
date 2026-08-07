"""Golden cases for linear.residual_norms (v2.3 Wave A)."""

from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_pythagorean_norms_match_closed_form() -> None:
    golden = GoldenCase(
        id="pythagorean.json",
        skill_id="linear.residual_norms",
        skill_version="0.1.0",
        inputs={"r": [3.0, 4.0]},
        expected_result={
            "l1": 7.0,
            "l2": 5.0,
            "linf": 4.0,
            "n": 2,
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-9,
        source="closed form: L1, L2, Linf of the 3-4 Pythagorean vector",
        justification="|3|+|4|=7, sqrt(9+16)=5, max(|3|,|4|)=4.",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_zero_residual_has_zero_norms() -> None:
    out = implementation.execute({"r": [0.0, 0.0, 0.0]})
    assert out["result"]["l1"] == 0.0
    assert out["result"]["l2"] == 0.0
    assert out["result"]["linf"] == 0.0
    assert out["result"]["n"] == 3