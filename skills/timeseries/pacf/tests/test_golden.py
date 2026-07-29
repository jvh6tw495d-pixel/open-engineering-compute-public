"""Golden cases for timeseries.pacf (v2.5.1)."""

from __future__ import annotations

import math
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_alternating_series_matches_hand_derived_reflection_coefficients() -> None:
    """See references.md: pacf = [1, -0.75, -1/7, 1/6], derived from the
    Levinson-Durbin recursion on the hand-verified biased ACF."""
    golden = GoldenCase(
        id="alternating.json",
        skill_id="timeseries.pacf",
        skill_version="0.1.0",
        inputs={"series": [1.0, -1.0, 1.0, -1.0], "nlags": 3},
        expected_result={
            "pacf": [1.0, -0.75, -1.0 / 7.0, 1.0 / 6.0],
            "n": 4,
            "nlags": 3,
            "method": "levinson-durbin",
            "order_reached": 3,
            "is_positive_definite": True,
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-9,
        source="hand-derived Levinson-Durbin recursion (see references.md)",
        justification="reflection coefficients at k=1,2,3 computed by hand from the biased ACF",
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_pacf_lag0_is_always_one() -> None:
    out = implementation.execute({"series": [3.0, 1.0, 4.0, 1.0, 5.0, 9.0], "nlags": 2})
    assert out["result"]["pacf"][0] == 1.0


def test_biased_acf_guarantees_full_order_reached() -> None:
    out = implementation.execute({"series": [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0], "nlags": 4})
    assert out["result"]["is_positive_definite"] is True
    assert out["result"]["order_reached"] == 4
    assert math.isfinite(out["result"]["pacf"][-1])
