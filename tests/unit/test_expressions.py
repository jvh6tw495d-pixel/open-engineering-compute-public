import math

import pytest

from oec.kernel.numerics.expressions import ExpressionError, compile_expression


@pytest.mark.parametrize(
    ("expression", "value", "expected"),
    [
        ("x", 3.0, 3.0),
        ("x**2 - 2", 1.5, 0.25),
        ("2*x + 1", 5.0, 11.0),
        ("x/2", 10.0, 5.0),
        ("-x", 4.0, -4.0),
        ("+x", 4.0, 4.0),
        ("sin(x)", 0.0, 0.0),
        ("cos(x)", 0.0, 1.0),
        ("sqrt(x)", 4.0, 2.0),
        ("abs(x)", -3.0, 3.0),
        ("exp(x)", 0.0, 1.0),
        ("log(e)", 1.0, 1.0),
        ("pi", 1.0, math.pi),
        ("x % 3", 7.0, 1.0),
    ],
)
def test_valid_expressions_evaluate_correctly(
    expression: str, value: float, expected: float
) -> None:
    f = compile_expression(expression)
    assert math.isclose(f(value), expected, abs_tol=1e-12)


def test_custom_symbol_name() -> None:
    f = compile_expression("t**2", symbol="t")
    assert f(3.0) == 9.0


@pytest.mark.parametrize("bad", ["", "   "])
def test_empty_expression_is_rejected(bad: str) -> None:
    with pytest.raises(ExpressionError):
        compile_expression(bad)


@pytest.mark.parametrize(
    "expression",
    [
        "x.__class__",
        "x.__class__.__bases__",
        "().__class__.__bases__[0].__subclasses__()",
        "x; import os",
        '__import__("os").system("echo pwned")',
        'open("secret").read()',
        "[i for i in range(10)]",
        "lambda: 1",
        "x if x > 0 else -x",
        'eval("1")',
        "globals()",
        "not_a_symbol",
        "not_a_function(x)",
        "x ** x ** x ** x",  # allowed syntactically; separate DoS concern is the caller's job
    ],
)
def test_disallowed_expressions_are_rejected(expression: str) -> None:
    if expression == "x ** x ** x ** x":
        compile_expression(expression)  # sanity: this one IS allowed, just deep
        return
    with pytest.raises(ExpressionError):
        compile_expression(expression)


def test_keyword_arguments_are_rejected() -> None:
    with pytest.raises(ExpressionError):
        compile_expression("log(x, base=2)")


def test_boolean_constant_is_rejected() -> None:
    with pytest.raises(ExpressionError):
        compile_expression("x + True")


def test_syntax_error_is_wrapped_as_expression_error() -> None:
    with pytest.raises(ExpressionError):
        compile_expression("x +")


def test_evaluator_never_uses_eval_or_exec() -> None:
    """Structural guarantee, not just behavioral: no function in this module
    ever references the eval/exec builtins as a callable name."""
    import oec.kernel.numerics.expressions as module

    for name in ("compile_expression", "_validate_node", "_eval_node"):
        func = getattr(module, name)
        referenced_names = func.__code__.co_names
        assert "eval" not in referenced_names, f"{name} references eval"
        assert "exec" not in referenced_names, f"{name} references exec"
