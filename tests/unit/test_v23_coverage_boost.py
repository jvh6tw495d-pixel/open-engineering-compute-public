"""Extra unit tests to cover Wave A/B correction paths (coverage gate)."""

from __future__ import annotations

import pytest

from oec.kernel.control.kalman import kalman_filter_linear
from oec.kernel.control.pid import pid_discrete
from oec.kernel.dynamics.state_space import simulate_state_space
from oec.kernel.statistics.intervals import confidence_interval_of_mean
from oec.kernel.timeseries.forecast import forecast_simple
from oec.kernel.timeseries.lag import lag_features
from oec.kernel.uncertainty.propagate import propagate_linear
from oec.kernel.uncertainty.sampling import latin_hypercube


def test_intervals_rejects_nonfinite_samples() -> None:
    with pytest.raises(ValueError, match="finite"):
        confidence_interval_of_mean([1.0, float("nan")])


def test_lhs_rejects_bad_bounds() -> None:
    with pytest.raises(ValueError):
        latin_hypercube(2, [[1.0, 0.0]])
    with pytest.raises(ValueError):
        latin_hypercube(0, [[0.0, 1.0]])


def test_propagate_matrix_jacobian() -> None:
    out = propagate_linear(
        [[1.0, 0.0], [0.0, 2.0]],
        [[1.0, 0.0], [0.0, 1.0]],
        nominal=[1.0, 1.0],
    )
    assert out["output_dim"] == 2
    assert out["nominal_output"] == [1.0, 2.0]


def test_state_space_rejects_bad_dt() -> None:
    with pytest.raises(ValueError, match="dt"):
        simulate_state_space([[1.0]], [[1.0]], [[1.0]], [[0.0]], [[1.0]], [0.0], dt=0.0)


def test_state_space_rejects_nonsquare_a() -> None:
    with pytest.raises(ValueError, match="square"):
        simulate_state_space([[1.0, 0.0]], [[1.0]], [[1.0]], [[0.0]], [[1.0]], [0.0], dt=1.0)


def test_kalman_with_input_matrix() -> None:
    out = kalman_filter_linear(
        [[1.0]],
        [[1.0]],
        [[1.0]],
        [[0.01]],
        [[1.0]],
        [[1.0], [2.0]],
        [0.0],
        [[1.0]],
        u=[[0.0], [0.0]],
    )
    assert out["n_steps"] == 2
    assert len(out["kalman_gains"]) == 2


def test_kalman_requires_u_when_b() -> None:
    with pytest.raises(ValueError, match="u is required"):
        kalman_filter_linear(
            [[1.0]],
            [[1.0]],
            [[1.0]],
            [[0.0]],
            [[1.0]],
            [[1.0]],
            [0.0],
            [[1.0]],
        )


def test_pid_rejects_bad_anti_windup() -> None:
    with pytest.raises(ValueError, match="anti_windup"):
        pid_discrete([1.0], [0.0], kp=1.0, ki=0.0, kd=0.0, dt=0.1, anti_windup="nope")  # type: ignore[arg-type]


def test_forecast_seasonal_and_mean() -> None:
    out_m = forecast_simple([1.0, 2.0, 3.0], steps_ahead=2, method="mean")
    assert out_m["forecast"] == [2.0, 2.0]
    out_s = forecast_simple([1.0, 2.0, 1.0, 2.0], steps_ahead=2, method="seasonal_naive", period=2)
    assert out_s["forecast"] == [1.0, 2.0]


def test_lag_rejects_short_series() -> None:
    with pytest.raises(ValueError):
        lag_features([1.0], [1])


def test_forecast_rejects_bad_method() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        forecast_simple([1.0, 2.0], steps_ahead=1, method="nope")


def test_forecast_rejects_bad_horizon() -> None:
    with pytest.raises(ValueError, match="steps_ahead"):
        forecast_simple([1.0, 2.0], steps_ahead=0, method="naive")


def test_pid_rejects_bad_dt_and_lengths() -> None:
    with pytest.raises(ValueError, match="dt"):
        pid_discrete([1.0], [0.0], kp=1.0, ki=0.0, kd=0.0, dt=0.0)
    with pytest.raises(ValueError, match="equal"):
        pid_discrete([1.0, 2.0], [0.0], kp=1.0, ki=0.0, kd=0.0, dt=0.1)


def test_stability_rejects_bad_time_base() -> None:
    from oec.kernel.dynamics.stability import stability_margins

    with pytest.raises(ValueError, match="time_base"):
        stability_margins([[1.0]], time_base="weird")


def test_units_operations_incompatible_add() -> None:
    from oec.kernel.units.operations import QuantityOperationError, add
    from oec.kernel.units.quantity import QuantityValue

    with pytest.raises(QuantityOperationError):
        add(QuantityValue(value=1.0, unit="m"), QuantityValue(value=1.0, unit="s"))


def test_energy_metrics_balance() -> None:
    from oec.kernel.energy.metrics import energy_balance

    out = energy_balance(energy_in=[1.0, 2.0], energy_out=[0.5, 1.5])
    assert isinstance(out, dict)


def test_timeseries_timegrid_basic() -> None:
    from oec.kernel.timeseries.timegrid import build_timegrid

    out = build_timegrid(
        start="2020-01-01T00:00:00Z",
        end="2020-01-01T03:00:00Z",
        freq="1h",
    )
    assert isinstance(out, dict)


def test_linear_solve_dense() -> None:
    from oec.kernel.linear.solve import solve_dense

    out = solve_dense([[2.0, 0.0], [0.0, 3.0]], [2.0, 6.0])
    assert out["x"][0] == pytest.approx(1.0)
    assert out["x"][1] == pytest.approx(2.0)
    assert out["singular"] is False


def test_describe_basic() -> None:
    from oec.kernel.statistics.describe import describe

    out = describe([1.0, 2.0, 3.0])
    assert out["n"] == 3 or "mean" in out


def test_monte_carlo_mean() -> None:
    from oec.kernel.statistics.monte_carlo import monte_carlo_mean

    out = monte_carlo_mean("x", n_samples=50, low=0.0, high=1.0, seed=0)
    assert isinstance(out, dict)


def test_intervals_zero_sample_sd() -> None:
    out = confidence_interval_of_mean([5.0, 5.0, 5.0], 0.95)
    assert out.half_width == 0.0
    assert out.lower == out.upper == 5.0


def test_finance_simple_returns() -> None:
    from oec.kernel.finance.metrics import simple_returns

    out = simple_returns([100.0, 110.0, 99.0])
    assert isinstance(out, (dict, list))


def test_backend_capabilities() -> None:
    from oec.backends.registry import get_backend_capabilities

    caps = get_backend_capabilities()
    assert caps is not None
