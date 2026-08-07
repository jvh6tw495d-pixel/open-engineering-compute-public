"""Golden cases for timeseries.levinson_durbin (v2.5.1)."""

from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_exact_ar1_geometric_acf_recovers_single_nonzero_coefficient() -> None:
    """r_k = 0.5^k is the exact ACF of an AR(1) process with phi=0.5.
    Fitting order 3 must recover [0.5, 0, 0] exactly (see references.md)."""
    golden = GoldenCase(
        id="exact_ar1.json",
        skill_id="timeseries.levinson_durbin",
        skill_version="0.1.0",
        inputs={"autocorrelation": [1.0, 0.5, 0.25, 0.125]},
        expected_result={
            "ar_coefficients": [0.5, 0.0, 0.0],
            "reflection_coefficients": [0.5, 0.0, 0.0],
            "prediction_error_variance": [1.0, 0.75, 0.75, 0.75],
            "ar_coefficients_by_order": [[0.5], [0.5, 0.0], [0.5, 0.0, 0.0]],
            "order_requested": 3,
            "order_reached": 3,
            "is_positive_definite": True,
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-9,
        source="exact AR(1) geometric autocorrelation, textbook property",
        justification=(
            "phi=r1/r0=0.5; every higher-order phi_k is exactly 0 for an exact AR(1) input"
        ),
    )
    out = implementation.execute(golden.inputs)
    assert_matches_golden(out["result"], golden)


def test_non_positive_definite_sequence_stops_honestly_and_does_not_raise() -> None:
    """r1 > r0 is impossible for a real autocorrelation sequence
    (Cauchy-Schwarz). The skill reports this rather than raising."""
    out = implementation.execute({"autocorrelation": [1.0, 1.5]})
    assert out["result"]["is_positive_definite"] is False
    assert out["result"]["order_reached"] == 0
    assert out["result"]["ar_coefficients"] == []
