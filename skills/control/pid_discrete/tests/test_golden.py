from __future__ import annotations

from pathlib import Path

from oec.testing import load_skill_module

_SKILL_DIR = Path(__file__).resolve().parent.parent
implementation = load_skill_module(_SKILL_DIR, "implementation")


def test_proportional_only() -> None:
    out = implementation.execute(
        {
            "reference": [1.0, 1.0, 1.0],
            "measurement": [0.0, 0.0, 0.0],
            "kp": 2.0,
            "ki": 0.0,
            "kd": 0.0,
            "dt": 0.1,
        }
    )["result"]
    assert out["u"] == [2.0, 2.0, 2.0]
    assert out["error"] == [1.0, 1.0, 1.0]


def test_derivative_only_ramp_error() -> None:
    """kp=ki=0: u[k] = kd*(e[k]-e[k-1])/dt. First step has no previous
    error (derivative=0); each later step differs by exactly 1."""
    out = implementation.execute(
        {
            "reference": [0.0, 1.0, 2.0, 3.0],
            "measurement": [0.0, 0.0, 0.0, 0.0],
            "kp": 0.0,
            "ki": 0.0,
            "kd": 2.0,
            "dt": 1.0,
        }
    )["result"]
    assert out["error"] == [0.0, 1.0, 2.0, 3.0]
    assert out["u"] == [0.0, 2.0, 2.0, 2.0]
    assert out["integral_term"] == [0.0, 0.0, 0.0, 0.0]


def test_integral_only_exact_cumulative_sum() -> None:
    """kp=kd=0: u[k] equals the integral term exactly, accumulating
    ki*dt*e each step (constant unit error, ki=0.5, dt=1)."""
    out = implementation.execute(
        {
            "reference": [1.0, 1.0, 1.0, 1.0],
            "measurement": [0.0, 0.0, 0.0, 0.0],
            "kp": 0.0,
            "ki": 0.5,
            "kd": 0.0,
            "dt": 1.0,
        }
    )["result"]
    assert out["u"] == [0.5, 1.0, 1.5, 2.0]
    assert out["integral_term"] == out["u"]


def test_anti_windup_none_keeps_integrating_through_saturation() -> None:
    """kp=ki=1, dt=1, constant error=10, u_max=5: every step is saturated
    from the first, and with anti_windup='none' the integral still
    accumulates the full candidate each step (hand-traced: integral_term
    = 10, 20, 30, 40)."""
    out = implementation.execute(
        {
            "reference": [10.0, 10.0, 10.0, 10.0],
            "measurement": [0.0, 0.0, 0.0, 0.0],
            "kp": 1.0,
            "ki": 1.0,
            "kd": 0.0,
            "dt": 1.0,
            "u_max": 5.0,
            "anti_windup": "none",
        }
    )["result"]
    assert out["u"] == [5.0, 5.0, 5.0, 5.0]
    assert out["integral_term"] == [10.0, 20.0, 30.0, 40.0]
    assert out["saturated_steps"] == 4


def test_anti_windup_clamp_freezes_integral_under_saturation() -> None:
    """Same inputs as the 'none' case above, but anti_windup='clamp':
    since the unsaturated command (20) exceeds u_max already at k=0, the
    integral is never committed and stays frozen at 0 for every step --
    a direct, hand-traceable contrast with the 'none' case."""
    out = implementation.execute(
        {
            "reference": [10.0, 10.0, 10.0, 10.0],
            "measurement": [0.0, 0.0, 0.0, 0.0],
            "kp": 1.0,
            "ki": 1.0,
            "kd": 0.0,
            "dt": 1.0,
            "u_max": 5.0,
            "anti_windup": "clamp",
        }
    )["result"]
    assert out["u"] == [5.0, 5.0, 5.0, 5.0]
    assert out["integral_term"] == [0.0, 0.0, 0.0, 0.0]
    assert out["saturated_steps"] == 4
