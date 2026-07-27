"""Structural and dimensional validation over the Math IR expression tree
(roadmap Step B item 3).

Unlike the runtime, bare-float expression evaluator in
:mod:`oec.kernel.numerics.expressions`, this module can answer "is this
expression dimensionally consistent" *before* any numeric evaluation, because
the tree is data, not an opaque string. Dimension composition is built on
:func:`oec.kernel.units.normalize.dimension_of`'s own stable string contract
(sorted dimension names, explicit exponents, ``*``-joined) rather than on
Pint's internal dimensionality algebra, keeping Pint an implementation detail
here exactly as it already is for :class:`~oec.kernel.units.quantity.QuantityValue`.

This is the first place :class:`~oec.core.errors.DimensionalIncompatibilityError`
is actually raised anywhere in the codebase — it has existed, unused, since
the v2.0 Scientific Kernel.
"""

from __future__ import annotations

from collections.abc import Mapping

from oec.core.errors import DimensionalIncompatibilityError
from oec.kernel.units.constants import get_constant
from oec.kernel.units.normalize import dimension_of
from oec.modeling.ir import (
    BinaryOp,
    ConstantRef,
    Equation,
    Expr,
    FunctionCall,
    NumberLiteral,
    QuantityLiteral,
    SymbolRef,
    UnaryOp,
)

DIMENSIONLESS = "dimensionless"

_DimensionParts = dict[str, float]


def _parse_dimension(dimension: str) -> _DimensionParts:
    if dimension == DIMENSIONLESS:
        return {}
    parts: _DimensionParts = {}
    for token in dimension.split("*"):
        name, _, exponent = token.partition("^")
        parts[name] = float(exponent)
    return parts


def _render_dimension(parts: _DimensionParts) -> str:
    nonzero = {name: exponent for name, exponent in parts.items() if exponent != 0}
    if not nonzero:
        return DIMENSIONLESS
    return "*".join(f"{name}^{exponent:g}" for name, exponent in sorted(nonzero.items()))


def _combine(left: _DimensionParts, right: _DimensionParts, sign: float) -> _DimensionParts:
    combined = dict(left)
    for name, exponent in right.items():
        combined[name] = combined.get(name, 0.0) + sign * exponent
    return combined


def _scale(parts: _DimensionParts, factor: float) -> _DimensionParts:
    return {name: exponent * factor for name, exponent in parts.items()}


def infer_dimension(expr: Expr, symbol_units: Mapping[str, str | None]) -> str:
    """Return the OEC-canonical dimension string for ``expr``.

    Raises :class:`DimensionalIncompatibilityError` for an unknown symbol, an
    addition/subtraction across incompatible dimensions, a non-dimensionless
    argument to a math function, or an exponent that isn't a literal number.
    """
    return _render_dimension(_dimension_parts(expr, symbol_units))


def _dimension_parts(expr: Expr, symbol_units: Mapping[str, str | None]) -> _DimensionParts:
    if isinstance(expr, NumberLiteral):
        return {}

    if isinstance(expr, QuantityLiteral):
        return _parse_dimension(dimension_of(expr.value.unit))

    if isinstance(expr, ConstantRef):
        try:
            constant = get_constant(expr.key)
        except KeyError as exc:
            raise DimensionalIncompatibilityError(str(exc), details={"key": expr.key}) from exc
        return _parse_dimension(dimension_of(constant.quantity.unit))

    if isinstance(expr, SymbolRef):
        if expr.name not in symbol_units:
            raise DimensionalIncompatibilityError(
                f"unknown symbol {expr.name!r}", details={"symbol": expr.name}
            )
        unit = symbol_units[expr.name]
        return {} if unit is None else _parse_dimension(dimension_of(unit))

    if isinstance(expr, UnaryOp):
        return _dimension_parts(expr.operand, symbol_units)

    if isinstance(expr, BinaryOp):
        left = _dimension_parts(expr.left, symbol_units)
        right = _dimension_parts(expr.right, symbol_units)

        if expr.op in ("+", "-"):
            if left != right:
                raise DimensionalIncompatibilityError(
                    f"cannot {expr.op!r} incompatible dimensions "
                    f"{_render_dimension(left)!r} and {_render_dimension(right)!r}",
                    details={
                        "op": expr.op,
                        "left": _render_dimension(left),
                        "right": _render_dimension(right),
                    },
                )
            return left

        if expr.op == "*":
            return _combine(left, right, 1.0)

        if expr.op == "/":
            return _combine(left, right, -1.0)

        if expr.op == "**":
            if not isinstance(expr.right, NumberLiteral):
                raise DimensionalIncompatibilityError(
                    "an exponent must be a literal number for dimensional inference",
                    details={"op": expr.op},
                )
            return _scale(left, expr.right.value)

        raise DimensionalIncompatibilityError(f"unsupported operator {expr.op!r}")

    if isinstance(expr, FunctionCall):
        for arg in expr.args:
            arg_parts = _dimension_parts(arg, symbol_units)
            if arg_parts:
                argument_dimension = _render_dimension(arg_parts)
                raise DimensionalIncompatibilityError(
                    f"function {expr.name!r} requires dimensionless arguments, "
                    f"got {argument_dimension!r}",
                    details={"function": expr.name, "argument_dimension": argument_dimension},
                )
        return {}

    raise DimensionalIncompatibilityError(f"unsupported expression node {type(expr).__name__}")


def check_equation_dimensions(equation: Equation, symbol_units: Mapping[str, str | None]) -> None:
    """Raise :class:`DimensionalIncompatibilityError` if ``lhs``/``rhs`` differ in dimension."""
    lhs_dimension = infer_dimension(equation.lhs, symbol_units)
    rhs_dimension = infer_dimension(equation.rhs, symbol_units)
    if lhs_dimension != rhs_dimension:
        raise DimensionalIncompatibilityError(
            f"equation sides have incompatible dimensions: {lhs_dimension!r} vs {rhs_dimension!r}",
            details={"lhs": lhs_dimension, "rhs": rhs_dimension},
        )


def referenced_symbols(expr: Expr) -> set[str]:
    """Return every symbol name referenced anywhere in ``expr``."""
    if isinstance(expr, SymbolRef):
        return {expr.name}
    if isinstance(expr, NumberLiteral | QuantityLiteral | ConstantRef):
        return set()
    if isinstance(expr, UnaryOp):
        return referenced_symbols(expr.operand)
    if isinstance(expr, BinaryOp):
        return referenced_symbols(expr.left) | referenced_symbols(expr.right)
    if isinstance(expr, FunctionCall):
        result: set[str] = set()
        for arg in expr.args:
            result |= referenced_symbols(arg)
        return result
    raise DimensionalIncompatibilityError(f"unsupported expression node {type(expr).__name__}")
