from __future__ import annotations

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
