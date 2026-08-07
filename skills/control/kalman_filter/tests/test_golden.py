from __future__ import annotations

import math
from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_two_step_scalar_recursion_matches_hand_derived_algebra() -> None:
    """A=C=1, Q=R=P0=1, x0=10, z=[0,0]. Step 1: p_pred=2, S=3, K=2/3,
    x1=10-20/3=10/3, p1=2/3. Step 2: p_pred=5/3, S=8/3, K=5/8,
    x2=x1*(1-5/8)=x1*3/8=1.25 -- hand-traced Joseph-form scalar algebra."""
    out = implementation.execute(
        {
            "A": [[1.0]],
            "C": [[1.0]],
            "Q": [[1.0]],
            "R": [[1.0]],
            "z": [[0.0], [0.0]],
            "x0": [10.0],
            "P0": [[1.0]],
        }
    )["result"]
    assert math.isclose(out["x_filtered"][0][0], 10.0 / 3.0, rel_tol=1e-9)
    assert math.isclose(out["x_filtered"][1][0], 1.25, abs_tol=1e-9)


def test_control_input_shifts_the_prediction() -> None:
    """A=B=C=1, Q=0, R=1, x0=0, u=3: predict x_pred=0+1*3=3 (not 0), then
    K=P_pred/(P_pred+R)=1/2, x1=3+0.5*(5-3)=4.0 exactly."""
    out = implementation.execute(
        {
            "A": [[1.0]],
            "B": [[1.0]],
            "C": [[1.0]],
            "Q": [[0.0]],
            "R": [[1.0]],
            "z": [[5.0]],
            "x0": [0.0],
            "P0": [[1.0]],
            "u": [[3.0]],
        }
    )["result"]
    assert math.isclose(out["x_filtered"][0][0], 4.0, abs_tol=1e-9)


def test_diagonal_two_state_system_decouples_exactly() -> None:
    """Diagonal A/C/Q/R/P0 means the two states evolve as two independent
    scalar filters in the same call: state 0 reproduces the two-step
    recursion's first step (10/3), state 1 reproduces the single-step
    static case from this file's first test (moves from 0 toward
    z=5 with P0=R=1, Q=0 -> 2.5)."""
    out = implementation.execute(
        {
            "A": [[1.0, 0.0], [0.0, 1.0]],
            "C": [[1.0, 0.0], [0.0, 1.0]],
            "Q": [[1.0, 0.0], [0.0, 0.0]],
            "R": [[1.0, 0.0], [0.0, 1.0]],
            "z": [[0.0, 5.0]],
            "x0": [10.0, 0.0],
            "P0": [[1.0, 0.0], [0.0, 1.0]],
        }
    )["result"]
    assert math.isclose(out["x_filtered"][0][0], 10.0 / 3.0, rel_tol=1e-9)
    assert math.isclose(out["x_filtered"][0][1], 2.5, abs_tol=1e-9)


def test_larger_process_noise_yields_larger_gain_and_closer_fit() -> None:
    """A=C=1, R=1, x0=0, P0=1, z=10, but Q=4 (vs. Q=0 in the static test):
    p_pred=1+4=5, S=6, K=5/6, x1=(5/6)*10=25/3 -- a larger process-noise
    prior pulls the estimate closer to the measurement than K=0.5 would."""
    out = implementation.execute(
        {
            "A": [[1.0]],
            "C": [[1.0]],
            "Q": [[4.0]],
            "R": [[1.0]],
            "z": [[10.0]],
            "x0": [0.0],
            "P0": [[1.0]],
        }
    )["result"]
    assert math.isclose(out["x_filtered"][0][0], 25.0 / 3.0, rel_tol=1e-9)


def test_static_scalar_moves_toward_measurement() -> None:
    out = implementation.execute(
        {
            "A": [[1.0]],
            "C": [[1.0]],
            "Q": [[0.0]],
            "R": [[1.0]],
            "z": [[5.0]],
            "x0": [0.0],
            "P0": [[1.0]],
        }
    )["result"]
    assert abs(out["x_filtered"][0][0] - 2.5) < 1e-12
    assert out["method"] == "discrete_linear_kalman_joseph"
    assert "p_filtered" in out
    assert "kalman_gains" in out
