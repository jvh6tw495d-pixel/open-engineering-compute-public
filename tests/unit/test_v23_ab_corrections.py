"""Adversarial tests for v2.3 Wave A/B correction package (A23/B23)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from oec.kernel.control.kalman import KalmanNumericalError, kalman_filter_linear
from oec.kernel.control.pid import pid_discrete
from oec.kernel.dynamics.stability import stability_margins
from oec.kernel.statistics.intervals import confidence_interval_of_mean
from oec.kernel.uncertainty.morris import morris_screen
from oec.kernel.uncertainty.propagate import propagate_linear

# --- A23-01 intervals ---


def test_z_interval_population_sigma_closed_form() -> None:
    z = float(stats.norm.ppf(0.975))
    half = z * 2.0 / math.sqrt(1)
    out = confidence_interval_of_mean([10.0], 0.95, population_standard_deviation=2.0)
    assert out.distribution == "gaussian"
    assert out.dispersion_used == "population_standard_deviation"
    assert out.half_width == pytest.approx(half)


def test_t_interval_matches_scipy() -> None:
    samples = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = confidence_interval_of_mean(samples, 0.95)
    mean = 3.0
    s = float(np.std(samples, ddof=1))
    lo, hi = stats.t.interval(0.95, 4, loc=mean, scale=s / math.sqrt(5))
    assert out.lower == pytest.approx(float(lo))
    assert out.upper == pytest.approx(float(hi))


def test_rejects_known_variance_flag() -> None:
    with pytest.raises(ValueError, match="known_variance"):
        confidence_interval_of_mean([1.0, 2.0], known_variance=True)  # type: ignore[call-arg]


@pytest.mark.parametrize("sigma", [0.0, -1.0, float("nan"), float("inf")])
def test_rejects_bad_population_sigma(sigma: float) -> None:
    with pytest.raises(ValueError):
        confidence_interval_of_mean([1.0], population_standard_deviation=sigma)


# --- B23-01 Kalman ---


def test_kalman_scalar_closed_form() -> None:
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
    p = np.asarray(out["p_filtered"][0])
    assert p[0, 0] == pytest.approx(0.5)
    assert np.allclose(p, p.T)


def test_kalman_rejects_negative_r() -> None:
    with pytest.raises(ValueError, match="R"):
        kalman_filter_linear([[1.0]], None, [[1.0]], [[0.0]], [[-1.0]], [[1.0]], [0.0], [[1.0]])


def test_kalman_rejects_nonsymmetric_q() -> None:
    with pytest.raises(ValueError, match="symmetric"):
        kalman_filter_linear(
            [[1.0, 0.0], [0.0, 1.0]],
            None,
            [[1.0, 0.0]],
            [[1.0, 2.0], [0.0, 1.0]],
            [[1.0]],
            [[0.0]],
            [0.0, 0.0],
            [[1.0, 0.0], [0.0, 1.0]],
        )


def test_kalman_r_zero_rejected_as_not_pd() -> None:
    with pytest.raises(ValueError, match="positive definite"):
        kalman_filter_linear([[1.0]], None, [[1.0]], [[0.0]], [[0.0]], [[1.0]], [0.0], [[1.0]])


def test_kalman_ill_conditioned_innovation() -> None:
    # Nearly singular 2-output R (positive definite but extreme cond)
    r = [[1e-18, 0.0], [0.0, 1e-18]]
    with pytest.raises((KalmanNumericalError, ValueError)):
        kalman_filter_linear(
            [[1.0]],
            None,
            [[1.0], [1.0]],
            [[0.0]],
            r,
            [[0.0, 0.0]],
            [0.0],
            [[1.0]],
        )


def test_kalman_p_remains_psd() -> None:
    out = kalman_filter_linear(
        [[0.9]],
        None,
        [[1.0]],
        [[0.1]],
        [[0.5]],
        [[1.0], [0.5], [0.0]],
        [0.0],
        [[1.0]],
    )
    for pf in out["p_filtered"]:
        m = np.asarray(pf)
        assert np.allclose(m, m.T, atol=1e-10)
        assert float(np.min(np.linalg.eigvalsh(m))) >= -1e-10


# --- B23-02 propagate ---


def test_propagate_nominal_length() -> None:
    with pytest.raises(ValueError, match="nominal length"):
        propagate_linear([1.0, 1.0], [[1.0, 0.0], [0.0, 1.0]], nominal=[1.0])


def test_propagate_nominal_nan() -> None:
    with pytest.raises(ValueError, match="finite"):
        propagate_linear(
            [1.0, 1.0],
            [[1.0, 0.0], [0.0, 1.0]],
            nominal=[1.0, float("nan")],
        )


def test_propagate_nominal_ok() -> None:
    out = propagate_linear([1.0, 2.0], [[1.0, 0.0], [0.0, 1.0]], nominal=[3.0, 4.0])
    assert out["nominal"] == [3.0, 4.0]
    assert out["nominal_output"] == [pytest.approx(11.0)]


# --- B23-03 Morris ---


def test_morris_rejects_odd_levels() -> None:
    with pytest.raises(ValueError, match="even"):
        morris_screen([[0.0, 1.0]], [1.0], n_levels=5, n_trajectories=2, seed=0)


def test_morris_accepts_even_levels() -> None:
    out = morris_screen(
        [[0.0, 1.0], [0.0, 1.0]],
        [2.0, 0.0],
        n_levels=4,
        n_trajectories=10,
        seed=0,
    )
    assert out["method"] == "morris_linear_screen"
    assert out["mu_star"][0] > out["mu_star"][1]


# --- B23-04 stability ---


def test_stability_continuous_classes() -> None:
    assert stability_margins([[-1.0]])["classification"] == "stable"
    assert stability_margins([[0.0]])["classification"] == "marginal"
    assert stability_margins([[1.0]])["classification"] == "unstable"
    assert stability_margins([[-1.0]])["margin_kind"] == ("spectral_pole_margin_not_gain_phase")


def test_stability_discrete_classes() -> None:
    assert stability_margins([[0.5]], time_base="discrete")["classification"] == "stable"
    assert stability_margins([[1.0]], time_base="discrete")["classification"] == "marginal"
    assert stability_margins([[1.5]], time_base="discrete")["classification"] == "unstable"


# --- B23-05 PID ---


def test_pid_windup_none_vs_clamp() -> None:
    r = [1.0] * 20
    y = [0.0] * 20
    common = dict(kp=0.0, ki=1.0, kd=0.0, dt=1.0, u_min=0.0, u_max=1.0)
    none = pid_discrete(r, y, anti_windup="none", **common)
    clamp = pid_discrete(r, y, anti_windup="clamp", **common)
    assert none["anti_windup"] == "none"
    assert clamp["anti_windup"] == "clamp"
    assert none["saturated_steps"] > 0
    # Under prolonged saturation, clamp keeps a smaller |integral_term| tail
    assert abs(clamp["integral_term"][-1]) <= abs(none["integral_term"][-1]) + 1e-12


def test_state_space_continuous_zoh() -> None:
    from oec.kernel.dynamics.state_space import simulate_state_space

    # Continuous integrator approx: A=0, B=1, C=1, D=0
    out = simulate_state_space(
        [[0.0]],
        [[1.0]],
        [[1.0]],
        [[0.0]],
        [[1.0], [1.0]],
        [0.0],
        dt=1.0,
        time_base="continuous",
    )
    assert out["time_base"] == "continuous"
    assert out["backend"] == "scipy"
    assert out["n_steps"] == 2


def test_check_bound_conflicts_helper() -> None:
    from oec.kernel.optimization.highs import LinearVariable, check_bound_conflicts

    issues = check_bound_conflicts(
        [LinearVariable(name="x", lower=2.0, upper=1.0, kind="continuous")]
    )
    assert issues and "x" in issues[0]
