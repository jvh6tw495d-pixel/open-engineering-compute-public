"""Math IR scalar-root compiler tests (ADR 0020)."""

from __future__ import annotations

import pytest

from oec.core.errors import DimensionalIncompatibilityError, ScientificDomainError
from oec.modeling.compile_scalar_root import compile_scalar_root
from oec.modeling.ir import BinaryOp, Equation, MathProblem, NumberLiteral, Symbol, SymbolRef

_SQUARE_MINUS_FOUR = Equation(
    lhs=BinaryOp(op="**", left=SymbolRef(name="x"), right=NumberLiteral(value=2)),
    rhs=NumberLiteral(value=4),
)


def test_compile_scalar_root_via_initial_guess() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x")],
        unknowns=["x"],
        initial_guess={"x": 3.0},
        equations=[_SQUARE_MINUS_FOUR],
    )
    result = compile_scalar_root(problem)
    assert result.root == pytest.approx(2.0, abs=1e-6)
    assert result.diagnostics.method == "secant"
    assert result.diagnostics.converged is True


def test_compile_scalar_root_via_bracket() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x")],
        unknowns=["x"],
        bracket={"x": (0.0, 10.0)},
        equations=[_SQUARE_MINUS_FOUR],
    )
    result = compile_scalar_root(problem)
    assert result.root == pytest.approx(2.0, abs=1e-9)
    assert result.diagnostics.method == "brentq"
    assert result.diagnostics.converged is True


def test_rejects_more_than_one_equation() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x")],
        unknowns=["x"],
        initial_guess={"x": 3.0},
        equations=[_SQUARE_MINUS_FOUR, _SQUARE_MINUS_FOUR],
    )
    with pytest.raises(ScientificDomainError):
        compile_scalar_root(problem)


def test_rejects_equation_with_extra_free_symbol() -> None:
    equation = Equation(lhs=SymbolRef(name="x"), rhs=SymbolRef(name="a"))
    problem = MathProblem(
        symbols=[Symbol(name="x"), Symbol(name="a")],
        unknowns=["x"],
        initial_guess={"x": 3.0},
        equations=[equation],
    )
    with pytest.raises(ScientificDomainError, match="additional free symbol"):
        compile_scalar_root(problem)


def test_rejects_dimensionally_inconsistent_equation() -> None:
    equation = Equation(lhs=SymbolRef(name="x"), rhs=NumberLiteral(value=4.0))
    problem = MathProblem(
        symbols=[Symbol(name="x", unit="m")],
        unknowns=["x"],
        initial_guess={"x": 3.0},
        equations=[equation],
    )
    with pytest.raises(DimensionalIncompatibilityError):
        compile_scalar_root(problem)
