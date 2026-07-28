from __future__ import annotations

import math
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_active_factor_has_larger_mu_star() -> None:
    out = implementation.execute(
        {
            "bounds": [[0.0, 1.0], [0.0, 1.0]],
            "coeffs": [3.0, 0.0],
            "n_trajectories": 30,
            "seed": 1,
        }
    )["result"]
    assert out["mu_star"][0] > out["mu_star"][1]
    assert abs(out["mu"][0] - 3.0) < 0.5


def test_linear_model_elementary_effects_are_exact() -> None:
    """For an exactly linear f(x) = intercept + c.x, every elementary
    effect (f1-f0)/dx equals c[j] exactly regardless of trajectory/seed
    (linearity cancels the other dimensions), so mu==mu_star==c and
    sigma==0 -- much stronger than an approximate bound."""
    out = implementation.execute(
        {
            "bounds": [[0.0, 1.0], [0.0, 1.0]],
            "coeffs": [5.0, 0.0],
            "intercept": 2.0,
            "n_trajectories": 1,
            "n_levels": 4,
            "seed": 42,
        }
    )["result"]
    assert math.isclose(out["mu"][0], 5.0, rel_tol=1e-9)
    assert out["mu"][1] == 0.0
    assert math.isclose(out["mu_star"][0], 5.0, rel_tol=1e-9)
    assert out["mu_star"][1] == 0.0
    assert out["sigma"] == [0.0, 0.0]


def test_negative_coefficient_1d_exact_recovery() -> None:
    out = implementation.execute(
        {
            "bounds": [[-2.0, 2.0]],
            "coeffs": [-3.0],
            "n_trajectories": 5,
            "n_levels": 6,
            "seed": 7,
        }
    )["result"]
    assert math.isclose(out["mu"][0], -3.0, rel_tol=1e-9)
    assert math.isclose(out["mu_star"][0], 3.0, rel_tol=1e-9)
