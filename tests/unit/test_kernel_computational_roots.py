import math

import pytest

from oec.errors import NumericalDomainError
from oec.kernel.computational.roots import (
    find_root_bracketed,
    find_root_from_guess,
    select_default_method,
    solve_root_system,
)
from oec.kernel.numerics.expressions import compile_expression

_SQRT2_EXPR = "x**2 - 2"


@pytest.mark.parametrize("method", ["brentq", "bisect"])
def test_bracketed_methods_find_sqrt_two(method: str) -> None:
    f = compile_expression(_SQRT2_EXPR)
    result = find_root_bracketed(f, 0.0, 2.0, method=method)  # type: ignore[arg-type]
    assert math.isclose(result.root, math.sqrt(2), rel_tol=1e-8)
    assert result.diagnostics.converged is True
    assert result.diagnostics.method == method
    assert result.diagnostics.residual < 1e-8


def test_secant_finds_sqrt_two() -> None:
    f = compile_expression(_SQRT2_EXPR)
    result = find_root_from_guess(f, 1.0)
    assert math.isclose(result.root, math.sqrt(2), rel_tol=1e-8)
    assert result.diagnostics.method == "secant"
    assert result.diagnostics.converged is True


def test_newton_with_fprime_finds_sqrt_two() -> None:
    f = compile_expression(_SQRT2_EXPR)
    fprime = compile_expression("2*x")
    result = find_root_from_guess(f, 1.0, method="newton", fprime=fprime)
    assert math.isclose(result.root, math.sqrt(2), rel_tol=1e-8)
    assert result.diagnostics.method == "newton"


def test_newton_without_fprime_is_rejected() -> None:
    f = compile_expression(_SQRT2_EXPR)
    with pytest.raises(NumericalDomainError):
        find_root_from_guess(f, 1.0, method="newton")


def test_secant_with_fprime_is_rejected() -> None:
    f = compile_expression(_SQRT2_EXPR)
    with pytest.raises(NumericalDomainError):
        find_root_from_guess(f, 1.0, method="secant", fprime=compile_expression("2*x"))


def test_bad_bracket_without_sign_change_is_rejected() -> None:
    f = compile_expression(_SQRT2_EXPR)
    with pytest.raises(NumericalDomainError):
        find_root_bracketed(f, 0.0, 1.0)  # f(0)=-2, f(1)=-1: no sign change


def test_unknown_bracketed_method_is_rejected() -> None:
    f = compile_expression(_SQRT2_EXPR)
    with pytest.raises(NumericalDomainError):
        find_root_bracketed(f, 0.0, 2.0, method="not_a_method")  # type: ignore[arg-type]


def test_low_maxiter_yields_unconverged_not_an_exception() -> None:
    """Non-convergence is a diagnostic outcome (ADR 0007), never raised."""
    f = compile_expression(_SQRT2_EXPR)
    result = find_root_bracketed(f, 0.0, 2.0, max_iterations=1)
    assert result.diagnostics.converged is False


@pytest.mark.parametrize(
    ("has_bracket", "has_initial_guess", "expected"),
    [
        (True, False, "brentq"),
        (True, True, "brentq"),
        (False, True, "secant"),
    ],
)
def test_select_default_method(has_bracket: bool, has_initial_guess: bool, expected: str) -> None:
    assert (
        select_default_method(has_bracket=has_bracket, has_initial_guess=has_initial_guess)
        == expected
    )


def test_select_default_method_with_neither_input_is_rejected() -> None:
    with pytest.raises(NumericalDomainError):
        select_default_method(has_bracket=False, has_initial_guess=False)


def test_solve_root_system_recovers_a_linear_system() -> None:
    # x + y = 3, x - y = 1 -> x=2, y=1
    result = solve_root_system(lambda v: [v[0] + v[1] - 3, v[0] - v[1] - 1], [0.0, 0.0])
    assert math.isclose(result.x[0], 2.0, abs_tol=1e-8)
    assert math.isclose(result.x[1], 1.0, abs_tol=1e-8)
    assert result.diagnostics.converged is True
    assert result.diagnostics.backend == "scipy"
    assert result.diagnostics.residual is not None
    assert result.diagnostics.residual < 1e-8


def test_solve_root_system_default_method_is_hybr() -> None:
    result = solve_root_system(lambda v: [v[0] - 5.0], [0.0])
    assert result.diagnostics.method == "hybr"
