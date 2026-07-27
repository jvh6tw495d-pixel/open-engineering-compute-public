"""Unit tests for v2.3 Wave B kernels."""

from __future__ import annotations

import pytest

from oec.kernel.control.kalman import kalman_filter_linear
from oec.kernel.control.pid import pid_discrete
from oec.kernel.dynamics.stability import stability_margins
from oec.kernel.dynamics.state_space import simulate_state_space
from oec.kernel.uncertainty.morris import morris_screen
from oec.kernel.uncertainty.propagate import propagate_linear
from oec.kernel.uncertainty.sampling import latin_hypercube


def test_lhs_shape_and_seed() -> None:
    a = latin_hypercube(8, [[0.0, 1.0], [10.0, 20.0]], seed=3)
    b = latin_hypercube(8, [[0.0, 1.0], [10.0, 20.0]], seed=3)
    assert a["samples"] == b["samples"]
    assert a["n_dim"] == 2
    for row in a["samples"]:
        assert 0.0 <= row[0] <= 1.0
        assert 10.0 <= row[1] <= 20.0


def test_morris_linear_coeff() -> None:
    out = morris_screen(
        [[0.0, 1.0], [0.0, 1.0]],
        [4.0, 0.0],
        n_trajectories=25,
        seed=2,
    )
    assert out["mu_star"][0] > out["mu_star"][1]
    assert out["mu"][0] == pytest.approx(4.0, abs=0.5)


def test_propagate_linear_scalar() -> None:
    out = propagate_linear([1.0, 2.0], [[1.0, 0.0], [0.0, 1.0]])
    assert out["variance"] == pytest.approx(5.0)
    assert out["std"] == pytest.approx(5.0**0.5)


def test_state_space_integrator() -> None:
    out = simulate_state_space(
        [[1.0]],
        [[1.0]],
        [[1.0]],
        [[0.0]],
        [[1.0], [1.0]],
        [0.0],
        dt=1.0,
        time_base="discrete",
    )
    assert out["x"] == [[0.0], [1.0]]
    assert out["y"] == [[0.0], [1.0]]


def test_stability_continuous() -> None:
    out = stability_margins([[-3.0]], time_base="continuous")
    assert out["stable"] is True
    assert out["stability_margin"] == pytest.approx(3.0)


def test_pid_proportional() -> None:
    out = pid_discrete([1.0, 1.0], [0.0, 0.0], kp=3.0, ki=0.0, kd=0.0, dt=0.1)
    assert out["u"] == [3.0, 3.0]


def test_kalman_static() -> None:
    out = kalman_filter_linear(
        [[1.0]],
        None,
        [[1.0]],
        [[0.0]],
        [[1.0]],
        [[5.0]],
        [0.0],
        [[1.0]],
    )
    assert out["x_filtered"][0][0] == pytest.approx(2.5)
