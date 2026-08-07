"""Unit tests for linear.matrix_properties kernel (S13)."""

from __future__ import annotations

import pytest

from oec.kernel.linear.analysis import matrix_properties


def test_diagonal_matrix_properties() -> None:
    out = matrix_properties([[2.0, 0.0], [0.0, 3.0]])
    assert out["shape"] == [2, 2]
    assert out["rank"] == 2
    assert out["condition_number"] == pytest.approx(1.5, rel=1e-6)
    assert sorted(out["singular_values"], reverse=True) == pytest.approx([3.0, 2.0], rel=1e-6)
    assert len(out["eigenvalues_real"]) == 2


def test_rectangular_rank() -> None:
    out = matrix_properties([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    assert out["shape"] == [2, 3]
    assert out["rank"] == 2
    assert "eigenvalues_real" not in out
    assert len(out["singular_values"]) == 2
