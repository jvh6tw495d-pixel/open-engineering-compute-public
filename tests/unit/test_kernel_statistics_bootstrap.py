"""Unit tests for oec.kernel.statistics.bootstrap (v2.3 Wave A)."""

from __future__ import annotations

import math

import pytest

from oec.kernel.statistics.bootstrap import _statistic, bootstrap_ci


def test_statistic_helper_mean_and_median() -> None:
    from numpy import array
    assert _statistic(array([1.0, 2.0, 3.0]), "mean") == 2.0
    assert _statistic(array([1.0, 2.0, 3.0]), "median") == 2.0


def test_statistic_helper_variance_for_two_samples() -> None:
    from numpy import array
    # variance sample (ddof=1): mean=5, sum_sq=50, /(n-1)=50
    assert _statistic(array([0.0, 10.0]), "variance") == 50.0
    assert _statistic(array([10.0]), "variance") == 0.0


def test_statistic_helper_unknown_kind_raises() -> None:
    from numpy import array
    with pytest.raises(ValueError):
        _statistic(array([1.0]), "mode")


def test_invalid_confidence_level_raises() -> None:
    with pytest.raises(ValueError):
        bootstrap_ci([1.0, 2.0], confidence_level=0.0)
    with pytest.raises(ValueError):
        bootstrap_ci([1.0, 2.0], confidence_level=1.0)


def test_invalid_n_resamples_raises() -> None:
    with pytest.raises(ValueError):
        bootstrap_ci([1.0, 2.0], n_resamples=0)


def test_two_dimensional_series_raises() -> None:
    with pytest.raises(ValueError):
        bootstrap_ci([[1.0, 2.0], [3.0, 4.0]])  # type: ignore[arg-type]


def test_empty_series_raises() -> None:
    with pytest.raises(ValueError):
        bootstrap_ci([])


def test_unsupported_statistic_raises() -> None:
    with pytest.raises(ValueError):
        bootstrap_ci([1.0, 2.0, 3.0], statistic="mode")


def test_bootstrap_variance_ci_is_finite() -> None:
    out = bootstrap_ci(
        [1.0, 2.0, 3.0, 4.0, 5.0],
        statistic="variance",
        n_resamples=200,
        seed=1,
    )
    assert out.statistic == "variance"
    assert out.point_estimate > 0
    assert math.isfinite(out.lower) and math.isfinite(out.upper)


def test_bootstrap_median_ci_runs() -> None:
    out = bootstrap_ci([1.0, 2.0, 3.0, 4.0, 5.0], statistic="median", n_resamples=200, seed=1)
    assert out.point_estimate == 3.0
    assert out.backend == "numpy"
    assert out.confidence_level == 0.95