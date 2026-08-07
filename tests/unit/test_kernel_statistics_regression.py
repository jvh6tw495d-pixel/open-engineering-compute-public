"""Unit tests for oec.kernel.statistics.regression (v2.3 Wave A)."""

from __future__ import annotations

import pytest

from oec.kernel.statistics.regression import linear_regression


def test_non_2d_x_raises() -> None:
    with pytest.raises(ValueError):
        linear_regression([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])  # type: ignore[arg-type]


def test_non_1d_y_raises() -> None:
    with pytest.raises(ValueError):
        linear_regression([[1.0, 2.0], [3.0, 4.0]], [[1.0], [2.0]])  # type: ignore[arg-type]


def test_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        linear_regression([[1.0, 2.0], [3.0, 4.0]], [1.0, 2.0, 3.0])


def test_underdetermined_raises() -> None:
    with pytest.raises(ValueError):
        linear_regression([[1.0, 2.0, 3.0]], [1.0])


def test_zero_total_sum_of_squares_gives_zero_r_squared() -> None:
    """When y is constant, ss_tot = 0 and r_squared must be 0 by convention."""
    out = linear_regression(
        [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0], [1.0, 3.0]],
        [4.0, 4.0, 4.0, 4.0],
    )
    assert all(abs(f - 4.0) < 1e-9 for f in out.fitted)
    assert out.r_squared == 0.0
    assert abs(out.coefficients[1]) < 1e-9
