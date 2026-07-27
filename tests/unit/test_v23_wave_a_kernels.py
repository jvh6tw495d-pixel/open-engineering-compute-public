"""Unit tests for v2.3 Wave A kernel helpers (domain-independent)."""

from __future__ import annotations

import math

import pytest

from oec.kernel.linear.analysis import eigendecomposition, least_squares, residual_norms
from oec.kernel.statistics.bootstrap import bootstrap_ci
from oec.kernel.statistics.intervals import confidence_interval_of_mean
from oec.kernel.statistics.regression import linear_regression
from oec.kernel.timeseries.backtest import backtest
from oec.kernel.timeseries.forecast import forecast_simple
from oec.kernel.timeseries.lag import lag_features


def test_eigendecomposition_diagonal() -> None:
    out = eigendecomposition([[1.0, 0.0], [0.0, 2.0]])
    paired = sorted(zip(out["eigenvalues_real"], out["eigenvalues_imag"], strict=True))
    assert paired[0][0] == pytest.approx(1.0)
    assert paired[1][0] == pytest.approx(2.0)
    assert out["n"] == 2
    assert out["converged"] is None


def test_eigendecomposition_rejects_nonsquare() -> None:
    with pytest.raises(ValueError, match="square"):
        eigendecomposition([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])


def test_least_squares_exact_line() -> None:
    # y = 1 + 2x on three points; design has intercept column.
    out = least_squares(
        [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]],
        [1.0, 3.0, 5.0],
    )
    assert out["solution"][0] == pytest.approx(1.0)
    assert out["solution"][1] == pytest.approx(2.0)
    assert out["rank"] == 2


def test_residual_norms_pythagorean() -> None:
    out = residual_norms([3.0, 4.0])
    assert out["l1"] == pytest.approx(7.0)
    assert out["l2"] == pytest.approx(5.0)
    assert out["linf"] == pytest.approx(4.0)


def test_linear_regression_perfect_fit() -> None:
    result = linear_regression(
        [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0], [1.0, 3.0]],
        [1.0, 3.0, 5.0, 7.0],
    )
    assert result.coefficients[0] == pytest.approx(1.0)
    assert result.coefficients[1] == pytest.approx(2.0)
    assert result.r_squared == pytest.approx(1.0)
    assert result.rmse == pytest.approx(0.0)


def test_confidence_interval_of_mean_contains_mean() -> None:
    result = confidence_interval_of_mean([1.0, 2.0, 3.0, 4.0, 5.0], 0.95)
    assert result.mean == pytest.approx(3.0)
    assert result.lower < result.mean < result.upper
    assert result.distribution == "student_t"


def test_bootstrap_ci_mean_seeded() -> None:
    result = bootstrap_ci(
        [1.0, 2.0, 3.0, 4.0, 5.0],
        statistic="mean",
        n_resamples=500,
        seed=0,
    )
    assert result.point_estimate == pytest.approx(3.0)
    assert result.lower <= result.point_estimate <= result.upper


def test_lag_features_alignment() -> None:
    out = lag_features([1.0, 2.0, 3.0, 4.0], [1])
    assert out["y"] == [2.0, 3.0, 4.0]
    assert out["columns"]["1"] == [1.0, 2.0, 3.0]
    assert out["n_keep"] == 3


def test_forecast_simple_naive() -> None:
    out = forecast_simple([1.0, 2.0, 3.0, 4.0], steps_ahead=2, method="naive")
    assert out["forecast"] == [4.0, 4.0]
    assert out["steps_ahead"] == 2


def test_backtest_constant_series_zero_error() -> None:
    out = backtest([7.0, 7.0, 7.0, 7.0], steps_ahead=1, method="naive")
    assert out["mae"] == pytest.approx(0.0)
    assert out["rmse"] == pytest.approx(0.0)
    assert all(math.isclose(e, 0.0) for e in out["errors"])
