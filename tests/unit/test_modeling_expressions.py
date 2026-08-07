"""Math IR string-expression parser tests (ADR 0020)."""

from __future__ import annotations

import pytest

from oec.kernel.numerics.expressions import ExpressionError
from oec.modeling.expressions import parse_expression
from oec.modeling.ir import BinaryOp, FunctionCall, NumberLiteral, SymbolRef, UnaryOp


def test_parses_binary_op() -> None:
    expr = parse_expression("x**2 - 4", symbols=("x",))
    assert isinstance(expr, BinaryOp)
    assert expr.op == "-"
    assert isinstance(expr.left, BinaryOp)
    assert expr.left.op == "**"
    assert isinstance(expr.left.left, SymbolRef)
    assert expr.left.left.name == "x"
    assert isinstance(expr.right, NumberLiteral)
    assert expr.right.value == 4.0


def test_parses_unary_op() -> None:
    expr = parse_expression("-x", symbols=("x",))
    assert isinstance(expr, UnaryOp)
    assert expr.op == "-"


def test_parses_function_call() -> None:
    expr = parse_expression("sin(x)", symbols=("x",))
    assert isinstance(expr, FunctionCall)
    assert expr.name == "sin"
    assert isinstance(expr.args[0], SymbolRef)


def test_named_constant_becomes_number_literal() -> None:
    expr = parse_expression("pi", symbols=("x",))
    assert isinstance(expr, NumberLiteral)


def test_empty_symbols_rejected() -> None:
    with pytest.raises(ExpressionError):
        parse_expression("1", symbols=())


def test_duplicate_symbols_rejected() -> None:
    with pytest.raises(ExpressionError):
        parse_expression("x + y", symbols=("x", "x"))


@pytest.mark.parametrize("expression", ["x % 3", "x // 2"])
def test_mod_and_floordiv_not_representable_in_ir(expression: str) -> None:
    """The kernel evaluator's whitelist accepts these; the IR deliberately does not
    (ADR 0020 non-goals: undefined dimensional behavior)."""
    with pytest.raises(ExpressionError):
        parse_expression(expression, symbols=("x",))


@pytest.mark.parametrize(
    "expression",
    [
        "x.__class__",
        "().__class__.__bases__[0].__subclasses__()",
        "x; import os",
        '__import__("os").system("echo pwned")',
        'eval("1")',
        "globals()",
        "not_a_function(x)",
    ],
)
def test_disallowed_expressions_are_rejected(expression: str) -> None:
    with pytest.raises(ExpressionError):
        parse_expression(expression, symbols=("x",))


def test_parser_never_uses_eval_or_exec() -> None:
    """Structural guarantee, not just behavioral: this module never references
    the eval/exec/compile builtins as a callable name."""
    import oec.modeling.expressions as module

    for name in ("parse_expression", "_to_expr"):
        func = getattr(module, name)
        referenced_names = func.__code__.co_names
        assert "eval" not in referenced_names, f"{name} references eval"
        assert "exec" not in referenced_names, f"{name} references exec"
        assert "compile" not in referenced_names, f"{name} references compile"
