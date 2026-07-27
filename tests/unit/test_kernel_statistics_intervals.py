"""Unit tests for oec.kernel.statistics.intervals (v2.3 A23-01)."""

from __future__ import annotations

import pytest

from oec.kernel.statistics.intervals import confidence_interval_of_mean


def test_invalid_confidence_level_raises() -> None:
    with pytest.raises(ValueError):
        confidence_interval_of_mean([1.0, 2.0], confidence_level=0.0)
    with pytest.raises(ValueError):
        confidence_interval_of_mean([1.0, 2.0], confidence_level=1.0)


def test_two_dimensional_series_raises() -> None:
    with pytest.raises(ValueError):
        confidence_interval_of_mean([[1.0, 2.0], [3.0, 4.0]])  # type: ignore[arg-type]


def test_empty_series_raises() -> None:
    with pytest.raises(ValueError):
        confidence_interval_of_mean([])


def test_single_sample_student_t_raises() -> None:
    with pytest.raises(ValueError):
        confidence_interval_of_mean([1.0])


def test_population_sigma_single_sample_ok() -> None:
    out = confidence_interval_of_mean([1.0], population_standard_deviation=2.0)
    assert out.distribution == "gaussian"
    assert out.df is None
    assert out.dispersion_used == "population_standard_deviation"
    assert out.half_width > 0.0


def test_population_sigma_gives_finite_interval() -> None:
    out = confidence_interval_of_mean(
        [1.0, 2.0, 3.0, 4.0],
        population_standard_deviation=1.0,
        confidence_level=0.9,
    )
    assert out.distribution == "gaussian"
    assert out.lower < out.mean < out.upper
    assert out.n == 4
