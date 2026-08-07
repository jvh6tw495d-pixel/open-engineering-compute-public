"""Math IR structural/dimensional validation tests (ADR 0020)."""

from __future__ import annotations

import pytest

from oec.core.errors import DimensionalIncompatibilityError
from oec.modeling.dimensions import check_equation_dimensions, infer_dimension, referenced_symbols
from oec.modeling.ir import BinaryOp, ConstantRef, Equation, FunctionCall, NumberLiteral, SymbolRef


def test_number_literal_is_dimensionless() -> None:
    assert infer_dimension(NumberLiteral(value=3.0), {}) == "dimensionless"


def test_symbol_ref_uses_declared_unit() -> None:
    dimension = infer_dimension(SymbolRef(name="v"), {"v": "m/s"})
    assert dimension == "[length]^1*[time]^-1"


def test_symbol_ref_dimensionless_when_unit_is_none() -> None:
    assert infer_dimension(SymbolRef(name="n"), {"n": None}) == "dimensionless"


def test_unknown_symbol_raises() -> None:
    with pytest.raises(DimensionalIncompatibilityError):
        infer_dimension(SymbolRef(name="missing"), {})


def test_addition_requires_same_dimension() -> None:
    expr = BinaryOp(op="+", left=SymbolRef(name="d1"), right=SymbolRef(name="d2"))
    units = {"d1": "m", "d2": "cm"}
    # same dimension (length), different unit -- allowed at the dimension level
    assert infer_dimension(expr, units) == "[length]^1"


def test_addition_across_incompatible_dimensions_raises() -> None:
    expr = BinaryOp(op="+", left=SymbolRef(name="d"), right=SymbolRef(name="t"))
    with pytest.raises(DimensionalIncompatibilityError):
        infer_dimension(expr, {"d": "m", "t": "s"})


def test_multiplication_combines_dimensions() -> None:
    expr = BinaryOp(op="*", left=SymbolRef(name="v"), right=SymbolRef(name="t"))
    dimension = infer_dimension(expr, {"v": "m/s", "t": "s"})
    assert dimension == "[length]^1"


def test_division_subtracts_dimensions() -> None:
    expr = BinaryOp(op="/", left=SymbolRef(name="d"), right=SymbolRef(name="t"))
    dimension = infer_dimension(expr, {"d": "m", "t": "s"})
    assert dimension == "[length]^1*[time]^-1"


def test_power_scales_dimension() -> None:
    expr = BinaryOp(op="**", left=SymbolRef(name="x"), right=NumberLiteral(value=2))
    dimension = infer_dimension(expr, {"x": "m"})
    assert dimension == "[length]^2"


def test_power_with_non_literal_exponent_raises() -> None:
    expr = BinaryOp(op="**", left=SymbolRef(name="x"), right=SymbolRef(name="n"))
    with pytest.raises(DimensionalIncompatibilityError):
        infer_dimension(expr, {"x": "m", "n": None})


def test_function_call_requires_dimensionless_args() -> None:
    expr = FunctionCall(name="sin", args=[SymbolRef(name="v")])
    with pytest.raises(DimensionalIncompatibilityError):
        infer_dimension(expr, {"v": "m/s"})


def test_function_call_accepts_dimensionless_args() -> None:
    expr = FunctionCall(name="sin", args=[SymbolRef(name="n")])
    assert infer_dimension(expr, {"n": None}) == "dimensionless"


def test_constant_ref_uses_catalogue_unit() -> None:
    expr = ConstantRef(key="speed_of_light_in_vacuum")
    assert infer_dimension(expr, {}) == "[length]^1*[time]^-1"


def test_check_equation_dimensions_passes_for_matching_sides() -> None:
    equation = Equation(
        lhs=SymbolRef(name="d"),
        rhs=BinaryOp(op="*", left=SymbolRef(name="v"), right=SymbolRef(name="t")),
    )
    check_equation_dimensions(equation, {"d": "m", "v": "m/s", "t": "s"})


def test_check_equation_dimensions_raises_for_mismatched_sides() -> None:
    equation = Equation(lhs=SymbolRef(name="d"), rhs=SymbolRef(name="v"))
    with pytest.raises(DimensionalIncompatibilityError):
        check_equation_dimensions(equation, {"d": "m", "v": "m/s"})


def test_referenced_symbols_collects_all_names() -> None:
    expr = BinaryOp(
        op="+",
        left=FunctionCall(name="sin", args=[SymbolRef(name="a")]),
        right=SymbolRef(name="b"),
    )
    assert referenced_symbols(expr) == {"a", "b"}


def test_referenced_symbols_empty_for_literal() -> None:
    assert referenced_symbols(NumberLiteral(value=1.0)) == set()
