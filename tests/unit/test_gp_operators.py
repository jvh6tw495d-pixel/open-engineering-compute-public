"""GP operator IR unit tests (no DEAP required)."""

from __future__ import annotations

import math

import pytest

from oec.kernel.evolutionary.gp_operators import (
    ALLOWED_OP_NAMES,
    eval_tree,
    protected_div,
    tree_depth,
    tree_size,
)


def test_eval_simple_expression() -> None:
    tree = {
        "op": "add",
        "args": [
            {"op": "mul", "args": [{"var": "x0"}, {"var": "x0"}]},
            {"const": 1.0},
        ],
    }
    assert eval_tree(tree, {"x0": 3.0}) == 10.0
    assert tree_size(tree) == 5
    assert tree_depth(tree) == 3


def test_protected_div_and_forbidden_op() -> None:
    assert protected_div(1.0, 0.0) == 1.0
    with pytest.raises(ValueError, match="not in allow-list"):
        eval_tree({"op": "eval", "args": [{"const": 1.0}]}, {})
    assert "add" in ALLOWED_OP_NAMES
    assert "sin" in ALLOWED_OP_NAMES


def test_trig() -> None:
    v = eval_tree({"op": "sin", "args": [{"const": 0.0}]}, {})
    assert math.isclose(v, 0.0, abs_tol=1e-12)
