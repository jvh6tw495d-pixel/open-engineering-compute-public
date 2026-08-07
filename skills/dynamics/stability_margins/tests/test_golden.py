from __future__ import annotations

import math
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_stable_continuous() -> None:
    out = implementation.execute({"A": [[-2.0]], "time_base": "continuous"})["result"]
    assert out["stable"] is True
    assert abs(out["stability_margin"] - 2.0) < 1e-12


def test_unstable_continuous() -> None:
    out = implementation.execute({"A": [[1.0]], "time_base": "continuous"})["result"]
    assert out["stable"] is False


def test_continuous_marginal_at_the_origin() -> None:
    """A single eigenvalue exactly at 0 is the continuous stability
    boundary: spectral abscissa = 0, margin = 0 exactly."""
    out = implementation.execute({"A": [[0.0]], "time_base": "continuous"})["result"]
    assert out["classification"] == "marginal"
    assert out["stable"] is False
    assert out["stability_margin"] == 0.0


def test_discrete_marginal_on_the_unit_circle() -> None:
    """Eigenvalue exactly at 1.0 is the discrete stability boundary:
    spectral radius = 1.0, margin = 1 - 1 = 0 exactly."""
    out = implementation.execute({"A": [[1.0]], "time_base": "discrete"})["result"]
    assert out["classification"] == "marginal"
    assert out["stable"] is False
    assert out["stability_margin"] == 0.0


def test_discrete_stable_diagonal_two_by_two() -> None:
    """Diagonal A has exact eigenvalues 0.5 and 0.25; the spectral radius
    (largest modulus) is exactly 0.5, giving margin = 1 - 0.5 = 0.5."""
    out = implementation.execute({"A": [[0.5, 0.0], [0.0, 0.25]], "time_base": "discrete"})[
        "result"
    ]
    assert out["classification"] == "stable"
    assert out["stable"] is True
    assert sorted(out["eigenvalues_real"]) == [0.25, 0.5]
    assert math.isclose(out["stability_margin"], 0.5, rel_tol=1e-12)


def test_discrete_unstable_outside_the_unit_circle() -> None:
    """Eigenvalue at 2.0: spectral radius = 2.0 > 1, margin = 1 - 2 = -1
    exactly, classified unstable."""
    out = implementation.execute({"A": [[2.0]], "time_base": "discrete"})["result"]
    assert out["classification"] == "unstable"
    assert out["stable"] is False
    assert out["stability_margin"] == -1.0
