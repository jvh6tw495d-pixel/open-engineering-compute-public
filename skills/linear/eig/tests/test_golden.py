"""Golden cases for linear.eig (v2.3 Wave A).

The diagonal case has independently-derivable eigenvalues; the companion
rotation has a complex eigenvalue pair whose expected values come from the
closed form `cos(theta) ± i sin(theta)`.
"""

from __future__ import annotations

import math
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def _golden_diagonal() -> GoldenCase:
    return GoldenCase(
        id="diagonal.json",
        skill_id="linear.eig",
        skill_version="0.1.0",
        inputs={"A": [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0]]},
        expected_result={
            "eigenvalues_real": [1.0, 2.0, 3.0],
            "eigenvalues_imag": [0.0, 0.0, 0.0],
            "n": 3,
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-9,
        source="closed form: eigenvalues of a diagonal matrix (independent of LAPACK)",
        justification="diag([1,2,3]) has eigenvalues 1, 2, 3 by definition.",
    )


def test_diagonal_eigenvalues_match_closed_form() -> None:
    golden = _golden_diagonal()
    out = implementation.execute(golden.inputs)
    actual = {
        "eigenvalues_real": out["result"]["eigenvalues_real"],
        "eigenvalues_imag": out["result"]["eigenvalues_imag"],
        "n": out["result"]["n"],
        "backend": out["result"]["backend"],
        "converged": out["result"]["converged"],
    }
    # Eigenvalues may be returned in any order; sort by real part for the
    # deterministic comparison.
    paired = sorted(
        zip(
            actual["eigenvalues_real"],
            actual["eigenvalues_imag"],
            strict=False,
        )
    )
    actual["eigenvalues_real"] = [r for r, _ in paired]
    actual["eigenvalues_imag"] = [i for _, i in paired]
    expected_paired = sorted(
        zip(
            golden.expected_result["eigenvalues_real"],
            golden.expected_result["eigenvalues_imag"],
            strict=False,
        )
    )
    golden.expected_result["eigenvalues_real"] = [r for r, _ in expected_paired]
    golden.expected_result["eigenvalues_imag"] = [i for _, i in expected_paired]
    assert_matches_golden(actual, golden)


def test_rotation_has_unit_magnitude_complex_eigenvalues() -> None:
    """A 2D rotation matrix
    [[cos θ, -sin θ], [sin θ, cos θ]] has eigenvalues cos θ ± i sin θ
    of magnitude 1 (closed-form from the definition of a rotation)."""
    theta = 0.4
    a = math.cos(theta)
    b = math.sin(theta)
    out = implementation.execute(
        {"A": [[a, -b], [b, a]]}
    )
    eig_real = out["result"]["eigenvalues_real"]
    eig_imag = out["result"]["eigenvalues_imag"]
    assert out["result"]["converged"] is None
    magnitudes = [math.hypot(r, i) for r, i in zip(eig_real, eig_imag, strict=False)]
    for m in magnitudes:
        assert math.isclose(m, 1.0, rel_tol=1e-9, abs_tol=1e-12)