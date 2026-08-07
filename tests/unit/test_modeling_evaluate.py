"""Numeric evaluation tests for the Math IR (ADR 0020)."""

from __future__ import annotations

import math

import pytest

from oec.kernel.numerics.expressions import ExpressionError
from oec.kernel.units.quantity import QuantityValue
from oec.modeling.evaluate import evaluate_expr
from oec.modeling.ir import (
    BinaryOp,
    ConstantRef,
    FunctionCall,
    NumberLiteral,
    QuantityLiteral,
    SymbolRef,
    UnaryOp,
)


def test_number_literal() -> None:
    assert evaluate_expr(NumberLiteral(value=3.5), {}) == 3.5


def test_quantity_literal_returns_magnitude() -> None:
    literal = QuantityLiteral(value=QuantityValue(value=5.0, unit="m"))
    assert evaluate_expr(literal, {}) == 5.0


def test_constant_ref_returns_catalogue_magnitude() -> None:
    value = evaluate_expr(ConstantRef(key="speed_of_light_in_vacuum"), {})
    assert value == pytest.approx(299_792_458.0)


def test_symbol_ref_uses_binding() -> None:
    assert evaluate_expr(SymbolRef(name="x"), {"x": 7.0}) == 7.0


def test_symbol_ref_missing_binding_raises() -> None:
    with pytest.raises(ExpressionError):
        evaluate_expr(SymbolRef(name="x"), {})


@pytest.mark.parametrize(("op", "expected"), [("+", 4.0), ("-", -4.0)])
def test_unary_op(op: str, expected: float) -> None:
    expr = UnaryOp(op=op, operand=NumberLiteral(value=4.0))  # type: ignore[arg-type]
    assert evaluate_expr(expr, {}) == expected


@pytest.mark.parametrize(
    ("op", "left", "right", "expected"),
    [
        ("+", 2.0, 3.0, 5.0),
        ("-", 5.0, 3.0, 2.0),
        ("*", 4.0, 3.0, 12.0),
        ("/", 9.0, 3.0, 3.0),
        ("**", 2.0, 3.0, 8.0),
    ],
)
def test_binary_op(op: str, left: float, right: float, expected: float) -> None:
    expr = BinaryOp(op=op, left=NumberLiteral(value=left), right=NumberLiteral(value=right))  # type: ignore[arg-type]
    assert evaluate_expr(expr, {}) == pytest.approx(expected)


def test_function_call() -> None:
    expr = FunctionCall(name="sqrt", args=[NumberLiteral(value=9.0)])
    assert evaluate_expr(expr, {}) == pytest.approx(3.0)


def test_nested_expression_matches_math() -> None:
    # sin(x) + 2 * x, at x = 1.0
    expr = BinaryOp(
        op="+",
        left=FunctionCall(name="sin", args=[SymbolRef(name="x")]),
        right=BinaryOp(op="*", left=NumberLiteral(value=2.0), right=SymbolRef(name="x")),
    )
    assert evaluate_expr(expr, {"x": 1.0}) == pytest.approx(math.sin(1.0) + 2.0)
