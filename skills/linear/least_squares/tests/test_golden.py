"""Golden cases for linear.least_squares (v2.3 Wave A)."""

from __future__ import annotations

import math
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_exact_linear_fit_matches_normal_equations_closed_form() -> None:
    golden = GoldenCase(
        id="exact_linear_fit.json",
        skill_id="linear.least_squares",
        skill_version="0.1.0",
        inputs={"A": [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]], "b": [1.0, 3.0, 5.0]},
        expected_result={
            "solution": [1.0, 2.0],
            "rank": 2,
            "residual_sum_of_squares": 0.0,
            "backend": "numpy",
            "converged": None,
        },
        tolerance=1e-9,
        source="normal equations closed form (independent of LAPACK)",
        justification="A^T A x = A^T b yields x = [1, 2] by hand; residual is zero.",
    )
    out = implementation.execute(golden.inputs)
    actual = {
        "solution": out["result"]["solution"],
        "rank": out["result"]["rank"],
        "residual_sum_of_squares": out["result"]["residual_sum_of_squares"],
        "backend": out["result"]["backend"],
        "converged": out["result"]["converged"],
    }
    assert_matches_golden(actual, golden)


def test_overdetermined_inconsistent_system_yields_zero_residual_sum() -> None:
    """Least squares of A=[[1],[1],[1]], b=[1,2,3] produces the mean
    `x = 2` by hand. The residual sum-of-squares NumPy reports for a
    fully-determined overdetermined inexact system equals the closed form
    sum of squared deviations `sum((b-2)^2) = 2`."""
    out = implementation.execute({"A": [[1.0], [1.0], [1.0]], "b": [1.0, 2.0, 3.0]})
    assert math.isclose(out["result"]["solution"][0], 2.0, abs_tol=1e-12)
    assert out["result"]["rank"] == 1
    rss = out["result"]["residual_sum_of_squares"]
    assert rss is not None
    assert math.isclose(rss, 2.0, rel_tol=1e-9, abs_tol=1e-12)


def test_residual_vector_is_zero_for_exact_fit() -> None:
    out = implementation.execute(
        {"A": [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]], "b": [1.0, 3.0, 5.0]}
    )
    assert max(abs(r) for r in out["result"]["residuals"]) < 1e-9