import math

import pytest

from oec.errors import NumericalDomainError
from oec.kernel.numerics.expressions import compile_expression
from oec.kernel.optimization.scalar import minimize_scalar, select_default_method

_QUADRATIC = "(x - 3)**2"


def test_bounded_finds_minimum_inside_bounds() -> None:
    f = compile_expression(_QUADRATIC)
    result = minimize_scalar(f, bounds=(0.0, 10.0), method="bounded")
    assert math.isclose(result.x, 3.0, abs_tol=1e-6)
    assert math.isclose(result.fun, 0.0, abs_tol=1e-9)
    assert result.diagnostics.method == "bounded"
    assert result.diagnostics.converged is True


@pytest.mark.parametrize("method", ["brent", "golden"])
def test_unbounded_methods_find_minimum(method: str) -> None:
    f = compile_expression(_QUADRATIC)
    result = minimize_scalar(f, method=method)  # type: ignore[arg-type]
    assert math.isclose(result.x, 3.0, abs_tol=1e-4)
    assert result.diagnostics.method == method
    assert result.diagnostics.converged is True


def test_unknown_method_is_rejected() -> None:
    f = compile_expression(_QUADRATIC)
    with pytest.raises(NumericalDomainError):
        minimize_scalar(f, method="not_a_method")  # type: ignore[arg-type]


def test_bounded_without_bounds_is_rejected() -> None:
    f = compile_expression(_QUADRATIC)
    with pytest.raises(NumericalDomainError):
        minimize_scalar(f, method="bounded")


def test_bounds_with_non_bounded_method_is_rejected() -> None:
    f = compile_expression(_QUADRATIC)
    with pytest.raises(NumericalDomainError):
        minimize_scalar(f, bounds=(0.0, 10.0), method="brent")


def test_inverted_bounds_is_rejected() -> None:
    f = compile_expression(_QUADRATIC)
    with pytest.raises(NumericalDomainError):
        minimize_scalar(f, bounds=(10.0, 0.0), method="bounded")


def test_low_maxiter_yields_unconverged_not_an_exception() -> None:
    """Non-convergence is a diagnostic outcome (ADR 0007), never raised."""
    f = compile_expression(_QUADRATIC)
    result = minimize_scalar(f, bounds=(0.0, 10.0), method="bounded", max_iterations=1)
    assert result.diagnostics.converged is False


@pytest.mark.parametrize(
    ("has_bounds", "expected"),
    [(True, "bounded"), (False, "brent")],
)
def test_select_default_method(has_bounds: bool, expected: str) -> None:
    assert select_default_method(has_bounds=has_bounds) == expected
