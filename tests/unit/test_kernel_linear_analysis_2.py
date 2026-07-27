"""Unit tests for oec.kernel.linear.analysis v2.3 additions (eig/least_squares/residual_norms)."""

from __future__ import annotations

import pytest

from oec.kernel.linear.analysis import (
    eigendecomposition,
    least_squares,
    residual_norms,
)


def test_eig_non_square_raises() -> None:
    with pytest.raises(ValueError):
        eigendecomposition([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])


def test_eig_diagonal_returns_real_eigenpairs() -> None:
    out = eigendecomposition([[2.0, 0.0], [0.0, 3.0]])
    reals = sorted(out["eigenvalues_real"])
    assert reals == [2.0, 3.0]
    assert all(i == 0.0 for i in out["eigenvalues_imag"])
    assert out["converged"] is None
    assert out["n"] == 2


def test_least_squares_non_2d_raises() -> None:
    with pytest.raises(ValueError):
        least_squares([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])  # type: ignore[arg-type]


def test_least_squares_non_1d_b_raises() -> None:
    with pytest.raises(ValueError):
        least_squares([[1.0, 2.0], [3.0, 4.0]], [[1.0], [2.0]])  # type: ignore[arg-type]


def test_least_squares_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        least_squares([[1.0, 2.0], [3.0, 4.0]], [1.0, 2.0, 3.0])


def test_least_squares_residual_sum_of_squares_is_none_for_square_system() -> None:
    out = least_squares([[2.0, 0.0], [0.0, 3.0]], [4.0, 9.0])
    # Square system: residuals.size == 0 so rss stays None (per NumPy lstsq semantics)
    assert out["residual_sum_of_squares"] is None
    assert out["solution"] == [2.0, 3.0]
    assert out["rank"] == 2


def test_residual_norms_non_1d_raises() -> None:
    with pytest.raises(ValueError):
        residual_norms([[1.0, 2.0], [3.0, 4.0]])  # type: ignore[arg-type]


def test_residual_norms_pythagorean_matches_closed_form() -> None:
    out = residual_norms([3.0, 4.0])
    assert out["l1"] == 7.0
    assert out["l2"] == 5.0
    assert out["linf"] == 4.0
    assert out["n"] == 2
    assert out["converged"] is None


def test_residual_norms_empty_returns_zero_l_inf_safely() -> None:
    out = residual_norms([])
    assert out["linf"] == 0.0
    assert out["l1"] == 0.0
    assert out["l2"] == 0.0
    assert out["n"] == 0