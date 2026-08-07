"""Unified interpolation kernel tests (ADR 0022)."""

from __future__ import annotations

import math

import pytest

from oec.errors import NumericalDomainError
from oec.kernel.computational.interpolation import interpolate


def test_linear_interpolation() -> None:
    result = interpolate([0, 1, 2], [0, 1, 4], [0.5, 1.5], method="linear")
    assert result.values == pytest.approx([0.5, 2.5])
    assert result.diagnostics.backend == "numpy"
    assert result.diagnostics.converged is None


def test_cubic_spline_interpolation() -> None:
    result = interpolate([0, 1, 2, 3], [0, 1, 4, 9], [1.5], method="cubic_spline")
    assert math.isclose(result.values[0], 2.25, abs_tol=0.5)
    assert result.diagnostics.backend == "scipy"


def test_pchip_interpolation() -> None:
    result = interpolate([0, 1, 2, 3], [0, 1, 4, 9], [1.5], method="pchip")
    assert result.diagnostics.method == "pchip"
    assert result.diagnostics.backend == "scipy"


def test_diagnostics_never_reports_converged() -> None:
    """Closed-form construction + evaluation, not iterative (ADR 0013)."""
    result = interpolate([0, 1], [0, 1], [0.5], method="linear")
    assert result.diagnostics.converged is None


def test_unsupported_method_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        interpolate([0, 1], [0, 1], [0.5], method="not_a_method")  # type: ignore[arg-type]
