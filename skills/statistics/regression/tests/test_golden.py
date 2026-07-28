"""Golden cases for statistics.regression (v2.3 Wave A)."""

from __future__ import annotations

import math
from pathlib import Path

from oec.testing import load_skill_module
from oec.validation.golden import GoldenCase, assert_matches_golden

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_exact_linear_fit_matches_closed_form() -> None:
    golden = GoldenCase(
        id="exact_linear.json",
        skill_id="statistics.regression",
        skill_version="0.1.0",
        inputs={
            "x": [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0], [1.0, 3.0]],
            "y": [1.0, 3.0, 5.0, 7.0],
        },
        expected_result={
            "coefficients": [1.0, 2.0],
            "r_squared": 1.0,
            "rmse": 0.0,
            "residual_standard_error": 0.0,
            "n": 4,
            "k": 2,
            "backend": "numpy",
        },
        tolerance=1e-9,
        source="closed form: y = 2x + 1 over four exact samples",
        justification="Slope 2, intercept 1; R^2 = 1 and residual standard error = 0.",
    )
    out = implementation.execute(golden.inputs)
    actual = {
        "coefficients": out["result"]["coefficients"],
        "r_squared": out["result"]["r_squared"],
        "rmse": out["result"]["rmse"],
        "residual_standard_error": out["result"]["residual_standard_error"],
        "n": out["result"]["n"],
        "k": out["result"]["k"],
        "backend": out["result"]["backend"],
    }
    assert_matches_golden(actual, golden)


def test_perfect_linear_fit_yields_unit_r_squared() -> None:
    out = implementation.execute(
        {"x": [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0], [1.0, 3.0]], "y": [1.0, 3.0, 5.0, 7.0]}
    )
    assert math.isclose(out["result"]["r_squared"], 1.0, abs_tol=1e-12)
    assert max(abs(r) for r in out["result"]["residuals"]) < 1e-9


def test_two_feature_exact_fit_matches_closed_form() -> None:
    golden = GoldenCase(
        id="two_feature_exact.json",
        skill_id="statistics.regression",
        skill_version="0.1.0",
        inputs={
            "x": [
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [1.0, 0.0, 1.0],
                [1.0, 1.0, 1.0],
                [1.0, 2.0, 1.0],
            ],
            "y": [3.0, 5.0, 2.0, 4.0, 6.0],
        },
        expected_result={
            "coefficients": [3.0, 2.0, -1.0],
            "r_squared": 1.0,
            "rmse": 0.0,
            "residual_standard_error": 0.0,
            "n": 5,
            "k": 3,
            "backend": "numpy",
        },
        tolerance=1e-9,
        source="closed form: y = 3 + 2*x1 - 1*x2 over five exact samples",
        justification=(
            "Every row satisfies y = 3 + 2*x1 - x2 exactly, so the fit is exact "
            "(R^2 = 1, zero residual) with two real features plus the bias column."
        ),
    )
    out = implementation.execute(golden.inputs)
    actual = {
        "coefficients": out["result"]["coefficients"],
        "r_squared": out["result"]["r_squared"],
        "rmse": out["result"]["rmse"],
        "residual_standard_error": out["result"]["residual_standard_error"],
        "n": out["result"]["n"],
        "k": out["result"]["k"],
        "backend": out["result"]["backend"],
    }
    assert_matches_golden(actual, golden)


def test_minimum_samples_boundary_n_equals_k_plus_one() -> None:
    """n = k + 1 is the minimum overdetermined case (n_samples > n_features)."""
    out = implementation.execute({"x": [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]], "y": [3.0, 5.0, 7.0]})[
        "result"
    ]
    assert out["n"] == 3
    assert out["k"] == 2
    assert math.isclose(out["coefficients"][0], 3.0, abs_tol=1e-9)
    assert math.isclose(out["coefficients"][1], 2.0, abs_tol=1e-9)
    assert math.isclose(out["r_squared"], 1.0, abs_tol=1e-12)
    assert math.isclose(out["rmse"], 0.0, abs_tol=1e-9)
