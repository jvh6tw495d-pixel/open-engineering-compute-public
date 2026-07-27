"""Parse a string expression into a Math IR :data:`~oec.modeling.ir.Expr` tree.

Reuses :func:`oec.kernel.numerics.expressions.parse_and_validate` — the
exact same audited AST whitelist ``numerical.root_system`` and the other
existing expression-based skills already rely on — and only *transforms*
the already-validated tree into IR node objects. There is one audited
grammar in this codebase, not two; this module never calls ``eval``/``exec``.
"""

from __future__ import annotations

import ast

from oec.kernel.numerics.expressions import ALLOWED_CONSTANTS, ExpressionError, parse_and_validate
from oec.modeling.ir import BinaryOp, Expr, FunctionCall, NumberLiteral, SymbolRef, UnaryOp

_BINOP_SYMBOLS: dict[type[ast.operator], str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Pow: "**",
}
_UNARYOP_SYMBOLS: dict[type[ast.unaryop], str] = {
    ast.UAdd: "+",
    ast.USub: "-",
}


def parse_expression(expression: str, *, symbols: tuple[str, ...]) -> Expr:
    """Parse ``expression`` (over the named ``symbols``) into a Math IR tree.

    Same restrictions as :func:`~oec.kernel.numerics.expressions.compile_expression_vector`:
    ``symbols`` must be non-empty and duplicate-free. The Math IR grammar is a
    strict subset of the kernel evaluator's: ``%`` and ``//`` are accepted by
    the kernel whitelist but are deliberately not representable in the IR
    (their dimensional behavior is not well-defined for physical quantities;
    see ADR 0020's non-goals) and are rejected here even though
    :func:`~oec.kernel.numerics.expressions.parse_and_validate` allows them.
    """
    if not symbols:
        raise ExpressionError("symbols must not be empty")
    if len(set(symbols)) != len(symbols):
        raise ExpressionError(f"duplicate symbol names: {symbols}")

    validated = parse_and_validate(expression, symbols=frozenset(symbols))
    return _to_expr(validated)


def _to_expr(node: ast.expr) -> Expr:
    if isinstance(node, ast.BinOp):
        op = _BINOP_SYMBOLS.get(type(node.op))
        if op is None:
            raise ExpressionError(
                f"operator {type(node.op).__name__} is not representable in the Math IR"
            )
        return BinaryOp(op=op, left=_to_expr(node.left), right=_to_expr(node.right))

    if isinstance(node, ast.UnaryOp):
        op = _UNARYOP_SYMBOLS[type(node.op)]
        return UnaryOp(op=op, operand=_to_expr(node.operand))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            # Unreachable given parse_and_validate's prior check; guarded
            # explicitly (not via `assert`, which is stripped under -O).
            raise ExpressionError("only calls to a fixed set of math functions are allowed")
        return FunctionCall(name=node.func.id, args=[_to_expr(arg) for arg in node.args])

    if isinstance(node, ast.Name):
        if node.id in ALLOWED_CONSTANTS:
            return NumberLiteral(value=ALLOWED_CONSTANTS[node.id])
        return SymbolRef(name=node.id)

    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return NumberLiteral(value=float(node.value))

    raise ExpressionError(f"expression element {type(node).__name__} is not allowed")
