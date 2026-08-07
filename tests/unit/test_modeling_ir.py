"""Math IR v0 model tests (ADR 0020)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from oec.kernel.units.quantity import QuantityValue
from oec.modeling.ir import (
    BinaryOp,
    ConstantRef,
    Equation,
    FunctionCall,
    MathProblem,
    NumberLiteral,
    QuantityLiteral,
    Symbol,
    SymbolRef,
    UnaryOp,
)


def test_math_problem_linear_program_round_trips() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x", lower=0, upper=1), Symbol(name="y", lower=0, upper=1)],
        objective={"coeffs": {"x": 1, "y": 1}},
        constraints=[{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
    )
    assert problem.objective is not None
    assert problem.objective.coeffs == {"x": 1.0, "y": 1.0}
    assert len(problem.constraints) == 1


def test_math_problem_scalar_root_round_trips() -> None:
    equation = Equation(
        lhs=BinaryOp(op="**", left=SymbolRef(name="x"), right=NumberLiteral(value=2)),
        rhs=NumberLiteral(value=4),
    )
    problem = MathProblem(
        symbols=[Symbol(name="x")],
        unknowns=["x"],
        initial_guess={"x": 3.0},
        equations=[equation],
    )
    assert problem.equations == [equation]
    assert problem.initial_guess == {"x": 3.0}


def test_wrong_ir_version_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MathProblem(ir_version="9.9.9", symbols=[Symbol(name="x")], objective={"coeffs": {"x": 1}})


def test_duplicate_symbol_names_rejected() -> None:
    with pytest.raises(ValidationError):
        MathProblem(
            symbols=[Symbol(name="x"), Symbol(name="x")],
            objective={"coeffs": {"x": 1}},
        )


def test_symbol_bounds_inverted_rejected() -> None:
    with pytest.raises(ValidationError):
        MathProblem(
            symbols=[Symbol(name="x", lower=10, upper=0)],
            objective={"coeffs": {"x": 1}},
        )


def test_objective_referencing_unknown_symbol_rejected() -> None:
    with pytest.raises(ValidationError):
        MathProblem(symbols=[Symbol(name="x")], objective={"coeffs": {"y": 1}})


def test_unknowns_must_reference_declared_symbols() -> None:
    with pytest.raises(ValidationError):
        MathProblem(symbols=[Symbol(name="x")], unknowns=["y"])


def test_initial_guess_must_reference_declared_unknowns() -> None:
    with pytest.raises(ValidationError):
        MathProblem(symbols=[Symbol(name="x")], unknowns=["x"], initial_guess={"y": 1.0})


def test_symbol_rejects_unparseable_unit() -> None:
    with pytest.raises(ValidationError):
        Symbol(name="x", unit="not_a_real_unit_xyz")


def test_symbol_accepts_valid_unit() -> None:
    symbol = Symbol(name="v", unit="m/s")
    assert symbol.unit == "m/s"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_number_literal_rejects_non_finite(bad: float) -> None:
    with pytest.raises(ValidationError):
        NumberLiteral(value=bad)


def test_quantity_literal_wraps_quantity_value() -> None:
    literal = QuantityLiteral(value=QuantityValue(value=5.0, unit="m"))
    assert literal.value.unit == "m"


def test_constant_ref_rejects_unknown_key() -> None:
    with pytest.raises(ValidationError):
        ConstantRef(key="not_a_real_constant")


def test_constant_ref_accepts_known_key() -> None:
    ref = ConstantRef(key="speed_of_light_in_vacuum")
    assert ref.key == "speed_of_light_in_vacuum"


def test_function_call_rejects_unknown_name() -> None:
    with pytest.raises(ValidationError):
        FunctionCall(name="exec", args=[])


def test_function_call_accepts_allowed_name() -> None:
    call = FunctionCall(name="sqrt", args=[NumberLiteral(value=4)])
    assert call.name == "sqrt"


def test_unary_op_only_accepts_plus_minus() -> None:
    with pytest.raises(ValidationError):
        UnaryOp(op="!", operand=NumberLiteral(value=1))  # type: ignore[arg-type]


def test_expr_discriminated_union_round_trips_from_dict() -> None:
    equation = Equation.model_validate(
        {
            "lhs": {"kind": "symbol", "name": "x"},
            "rhs": {"kind": "number", "value": 2.0},
        }
    )
    assert isinstance(equation.lhs, SymbolRef)
    assert isinstance(equation.rhs, NumberLiteral)


def test_math_problem_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        MathProblem.model_validate(
            {
                "symbols": [{"name": "x"}],
                "objective": {"coeffs": {"x": 1}},
                "not_a_real_field": True,
            }
        )
