from __future__ import annotations

import math
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_discrete_integrator_ramp() -> None:
    out = implementation.execute(
        {
            "A": [[1.0]],
            "B": [[1.0]],
            "C": [[1.0]],
            "D": [[0.0]],
            "u": [[1.0], [1.0], [1.0]],
            "x0": [0.0],
            "dt": 1.0,
            "time_base": "discrete",
        }
    )["result"]
    assert out["x"] == [[0.0], [1.0], [2.0]]
    assert out["y"] == [[0.0], [1.0], [2.0]]


def test_continuous_exponential_decay_matches_closed_form() -> None:
    """A=[[-1]], zero input: ZOH reduces to x[k+1]=e^{-dt}*x[k], so with
    dt=1 the recorded states are 1.0, e^-1, e^-2 exactly."""
    out = implementation.execute(
        {
            "A": [[-1.0]],
            "B": [[0.0]],
            "C": [[1.0]],
            "D": [[0.0]],
            "u": [[0.0], [0.0], [0.0]],
            "x0": [1.0],
            "dt": 1.0,
            "time_base": "continuous",
        }
    )["result"]
    assert math.isclose(out["x"][0][0], 1.0, rel_tol=1e-12)
    assert math.isclose(out["x"][1][0], math.exp(-1.0), rel_tol=1e-9)
    assert math.isclose(out["x"][2][0], math.exp(-2.0), rel_tol=1e-9)
    assert out["y"] == out["x"]


def test_continuous_two_state_decoupled_decay() -> None:
    """Diagonal A means the two states evolve independently; each is the
    same exponential-decay closed form as the 1-D case, at its own rate."""
    out = implementation.execute(
        {
            "A": [[-1.0, 0.0], [0.0, -0.5]],
            "B": [[0.0, 0.0], [0.0, 0.0]],
            "C": [[1.0, 0.0], [0.0, 1.0]],
            "D": [[0.0, 0.0], [0.0, 0.0]],
            "u": [[0.0, 0.0], [0.0, 0.0]],
            "x0": [1.0, 2.0],
            "dt": 1.0,
            "time_base": "continuous",
        }
    )["result"]
    assert math.isclose(out["x"][0][0], 1.0, rel_tol=1e-12)
    assert math.isclose(out["x"][0][1], 2.0, rel_tol=1e-12)
    assert math.isclose(out["x"][1][0], math.exp(-1.0), rel_tol=1e-9)
    assert math.isclose(out["x"][1][1], 2.0 * math.exp(-0.5), rel_tol=1e-9)


def test_discrete_direct_feedthrough_contributes_to_output() -> None:
    """D != 0: the output includes a direct D*u term not present in the
    state, so y != x even though x follows the same integrator recursion."""
    out = implementation.execute(
        {
            "A": [[1.0]],
            "B": [[1.0]],
            "C": [[1.0]],
            "D": [[2.0]],
            "u": [[3.0], [1.0]],
            "x0": [0.0],
            "dt": 1.0,
            "time_base": "discrete",
        }
    )["result"]
    assert out["x"] == [[0.0], [3.0]]
    assert out["y"] == [[6.0], [5.0]]
