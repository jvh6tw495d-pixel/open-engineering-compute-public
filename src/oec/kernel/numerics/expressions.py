"""Safe evaluation of user-submitted mathematical expressions (plan section 4.7).

Plan instruction 4.7 is explicit: ``eval()``/``exec()`` are prohibited
for interpreting user-submitted expressions, full stop — not "prohibited
unless you're careful." This module never calls either. It parses via
the standard library ``ast`` module, walks the tree once to reject
anything outside a small whitelist (arithmetic, a fixed set of math
functions, one input symbol, numeric constants), and then *interprets*
that already-validated tree directly with a small recursive evaluator —
no compiled code object, no ``eval``.

A naive "just use SymPy's ``parse_expr``" approach was tried first and
rejected during development: even with a restricted ``global_dict`` and
``__builtins__`` blocked, SymPy's parser still accepts attribute-access
chains like ``().__class__.__bases__[0].__subclasses__()`` — a
well-known Python sandbox-escape technique — because SymPy's parser is
itself built on ``eval()``. Interpreting a whitelisted AST closes that
off structurally: ``ast.Attribute`` and ``ast.Subscript`` are simply
never in the allowed node set, so there is no attribute access to chain
through in the first place.
"""

from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable, Sequence

from oec.errors import OECValidationError

_ALLOWED_FUNCTIONS: dict[str, Callable[..., float]] = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "sqrt": math.sqrt,
    "abs": abs,
}
_ALLOWED_CONSTANTS: dict[str, float] = {"pi": math.pi, "e": math.e}
_BINOPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARYOPS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class ExpressionError(OECValidationError):
    """Raised when an expression contains anything outside the allowed grammar."""

    default_code = "expression_invalid"


def compile_expression(expression: str, *, symbol: str = "x") -> Callable[[float], float]:
    """Parse ``expression`` (a function of ``symbol``) into a safe callable.

    Raises :class:`ExpressionError` for empty input, a syntax error, or
    anything outside arithmetic + the allowed functions/constants above
    + ``symbol`` itself. The returned callable interprets the validated
    AST directly on every call — it never uses ``eval``/``exec``.
    """
    if not expression.strip():
        raise ExpressionError("expression must not be empty")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(
            f"invalid expression syntax: {exc}", details={"expression": expression}
        ) from exc

    validated = _validate_node(tree.body, frozenset({symbol}))

    def evaluate(value: float) -> float:
        return _eval_node(validated, {symbol: value})

    return evaluate


def compile_expression_vector(
    expression: str, *, symbols: tuple[str, ...]
) -> Callable[[Sequence[float]], float]:
    """Parse ``expression`` (a function of the named ``symbols``, in order)
    into a safe callable of a value vector.

    Same restricted-AST grammar and safety guarantee as
    :func:`compile_expression`, generalized to more than one independent
    variable — used for multi-variable objectives and constraints (e.g.
    ``mathematics.optimize_constrained``). ``symbols`` must be non-empty
    and duplicate-free; a name outside ``symbols``/the allowed constants
    is rejected exactly as an unknown name is in the scalar case.
    """
    if not expression.strip():
        raise ExpressionError("expression must not be empty")
    if not symbols:
        raise ExpressionError("symbols must not be empty")
    if len(set(symbols)) != len(symbols):
        raise ExpressionError(f"duplicate symbol names: {symbols}")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(
            f"invalid expression syntax: {exc}", details={"expression": expression}
        ) from exc

    validated = _validate_node(tree.body, frozenset(symbols))

    def evaluate(values: Sequence[float]) -> float:
        if len(values) != len(symbols):
            raise ExpressionError(
                f"expected {len(symbols)} values for symbols {symbols}, got {len(values)}"
            )
        return _eval_node(validated, dict(zip(symbols, values, strict=True)))

    return evaluate


def _validate_node(node: ast.AST, symbols: frozenset[str]) -> ast.expr:
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _BINOPS:
            raise ExpressionError(f"operator {type(node.op).__name__} is not allowed")
        _validate_node(node.left, symbols)
        _validate_node(node.right, symbols)
        return node

    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _UNARYOPS:
            raise ExpressionError(f"unary operator {type(node.op).__name__} is not allowed")
        _validate_node(node.operand, symbols)
        return node

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
            raise ExpressionError("only calls to a fixed set of math functions are allowed")
        if node.keywords:
            raise ExpressionError("keyword arguments are not allowed")
        for arg in node.args:
            _validate_node(arg, symbols)
        return node

    if isinstance(node, ast.Name):
        if node.id not in symbols and node.id not in _ALLOWED_CONSTANTS:
            raise ExpressionError(f"unknown name {node.id!r}")
        return node

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise ExpressionError(f"unsupported constant {node.value!r}")
        return node

    raise ExpressionError(f"expression element {type(node).__name__} is not allowed")


def _eval_node(node: ast.expr, bindings: dict[str, float]) -> float:
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, bindings)
        right = _eval_node(node.right, bindings)
        return _BINOPS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp):
        return _UNARYOPS[type(node.op)](_eval_node(node.operand, bindings))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            # Unreachable given _validate_node's prior check; guarded explicitly
            # (not via `assert`, which is stripped under -O) rather than trusted blindly.
            raise ExpressionError("only calls to a fixed set of math functions are allowed")
        func = _ALLOWED_FUNCTIONS[node.func.id]
        args = [_eval_node(arg, bindings) for arg in node.args]
        return float(func(*args))

    if isinstance(node, ast.Name):
        return bindings[node.id] if node.id in bindings else _ALLOWED_CONSTANTS[node.id]

    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)

    raise ExpressionError(f"expression element {type(node).__name__} is not allowed")
