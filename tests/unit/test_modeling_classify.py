"""Math IR deterministic problem classifier tests (ADR 0020)."""

from __future__ import annotations

import pytest

from oec.core.errors import (
    OverdeterminedProblemError,
    ScientificDomainError,
    UnderdeterminedProblemError,
)
from oec.modeling.classify import classify
from oec.modeling.ir import Equation, MathProblem, NumberLiteral, Symbol, SymbolRef

_EQUATION = Equation(lhs=SymbolRef(name="x"), rhs=NumberLiteral(value=2.0))


def test_objective_only_classifies_as_linear_program() -> None:
    problem = MathProblem(symbols=[Symbol(name="x")], objective={"coeffs": {"x": 1}})
    assert classify(problem) == "linear_program"


def test_equations_only_classifies_as_scalar_root() -> None:
    problem = MathProblem(symbols=[Symbol(name="x")], unknowns=["x"], equations=[_EQUATION])
    assert classify(problem) == "scalar_root"


def test_neither_objective_nor_equations_raises() -> None:
    problem = MathProblem(symbols=[Symbol(name="x")])
    with pytest.raises(ScientificDomainError):
        classify(problem)


def test_both_objective_and_equations_raises() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x")],
        objective={"coeffs": {"x": 1}},
        unknowns=["x"],
        equations=[_EQUATION],
    )
    with pytest.raises(ScientificDomainError):
        classify(problem)


def test_fewer_equations_than_unknowns_is_underdetermined() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x"), Symbol(name="y")],
        unknowns=["x", "y"],
        equations=[_EQUATION],
    )
    with pytest.raises(UnderdeterminedProblemError):
        classify(problem)


def test_more_equations_than_unknowns_is_overdetermined() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x")], unknowns=["x"], equations=[_EQUATION, _EQUATION]
    )
    with pytest.raises(OverdeterminedProblemError):
        classify(problem)


def test_explicit_class_matching_inferred_is_accepted() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x")],
        objective={"coeffs": {"x": 1}},
        problem_class="linear_program",
    )
    assert classify(problem) == "linear_program"


def test_explicit_class_mismatching_inferred_raises() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x")],
        unknowns=["x"],
        equations=[_EQUATION],
        problem_class="linear_program",
    )
    with pytest.raises(ScientificDomainError):
        classify(problem)
