"""Numeric evaluation of an already-validated Math IR expression tree.

Values are treated as plain magnitudes (units are checked for structural
*compatibility* by :mod:`oec.modeling.dimensions` before this runs, but are
not rescaled here) — see ADR 0020's v0 non-goals: callers must express
literals in mutually consistent units, the same boundary
``numerical.root_system`` already accepts today (it is entirely
dimensionless/bare-float). This evaluator reuses
:data:`oec.kernel.numerics.expressions.ALLOWED_FUNCTIONS`, the same audited
function whitelist as the string-expression evaluator — no ``eval``/``exec``.
"""

from __future__ import annotations

from collections.abc import Mapping

from oec.kernel.numerics.expressions import ALLOWED_FUNCTIONS, ExpressionError
from oec.kernel.units.constants import get_constant
from oec.modeling.ir import (
    BinaryOp,
    ConstantRef,
    Expr,
    FunctionCall,
    NumberLiteral,
    QuantityLiteral,
    SymbolRef,
    UnaryOp,
)


def evaluate_expr(expr: Expr, bindings: Mapping[str, float]) -> float:
    """Evaluate ``expr`` to a float, substituting ``bindings`` for symbols."""
    if isinstance(expr, NumberLiteral):
        return expr.value

    if isinstance(expr, QuantityLiteral):
        return expr.value.value

    if isinstance(expr, ConstantRef):
        try:
            constant = get_constant(expr.key)
        except KeyError as exc:
            raise ExpressionError(str(exc), details={"key": expr.key}) from exc
        return constant.quantity.value

    if isinstance(expr, SymbolRef):
        if expr.name not in bindings:
            raise ExpressionError(
                f"no binding for symbol {expr.name!r}", details={"symbol": expr.name}
            )
        return bindings[expr.name]

    if isinstance(expr, UnaryOp):
        value = evaluate_expr(expr.operand, bindings)
        return value if expr.op == "+" else -value

    if isinstance(expr, BinaryOp):
        left = evaluate_expr(expr.left, bindings)
        right = evaluate_expr(expr.right, bindings)
        if expr.op == "+":
            return left + right
        if expr.op == "-":
            return left - right
        if expr.op == "*":
            return left * right
        if expr.op == "/":
            return left / right
        if expr.op == "**":
            return float(left**right)
        raise ExpressionError(f"unsupported operator {expr.op!r}")

    if isinstance(expr, FunctionCall):
        func = ALLOWED_FUNCTIONS[expr.name]
        args = [evaluate_expr(arg, bindings) for arg in expr.args]
        return float(func(*args))

    raise ExpressionError(f"unsupported expression node {type(expr).__name__}")
