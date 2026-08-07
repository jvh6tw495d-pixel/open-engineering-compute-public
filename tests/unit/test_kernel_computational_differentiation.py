"""Finite-difference differentiation kernel tests (ADR 0022)."""

from __future__ import annotations

import math

import pytest

from oec.errors import NumericalDomainError
from oec.kernel.computational.differentiation import differentiate


def test_central_difference_of_quadratic_is_exact() -> None:
    """x**2's third derivative is zero, so central-difference truncation
    error vanishes identically -- only floating-point roundoff remains."""
    result = differentiate(lambda x: x**2, 3.0, method="central")
    assert result.value == pytest.approx(6.0, abs=1e-6)
    assert result.diagnostics.converged is None
    assert result.diagnostics.backend == "oec"


def test_forward_difference_of_sine_at_zero() -> None:
    result = differentiate(math.sin, 0.0, method="forward")
    assert result.value == pytest.approx(1.0, abs=1e-4)


def test_backward_difference_of_quadratic() -> None:
    result = differentiate(lambda x: x**2, 3.0, method="backward")
    assert result.value == pytest.approx(6.0, abs=1e-4)


def test_default_method_is_central() -> None:
    result = differentiate(lambda x: x**2, 2.0)
    assert result.diagnostics.method == "central"


def test_explicit_step_is_used_verbatim() -> None:
    result = differentiate(lambda x: x**2, 2.0, step=1e-3)
    assert result.diagnostics.model_dump()["step"] == 1e-3


def test_non_positive_step_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        differentiate(lambda x: x, 1.0, step=0.0)
    with pytest.raises(NumericalDomainError):
        differentiate(lambda x: x, 1.0, step=-1.0)


def test_unknown_method_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        differentiate(lambda x: x, 1.0, method="not_a_method")  # type: ignore[arg-type]
