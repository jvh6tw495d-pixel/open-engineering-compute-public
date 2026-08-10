"""Closed operator IR for genetic programming (E3) — no eval/exec."""

from __future__ import annotations

import math
import operator
from collections.abc import Callable
from typing import Any


def protected_div(left: float, right: float) -> float:
    if abs(right) < 1e-12:
        return 1.0
    return left / right


def protected_log(x: float) -> float:
    if x <= 0:
        return 0.0
    return math.log(x)


def protected_exp(x: float) -> float:
    # clamp to avoid overflow
    if x > 20:
        return math.exp(20)
    if x < -20:
        return math.exp(-20)
    return math.exp(x)


def protected_sqrt(x: float) -> float:
    return math.sqrt(abs(x))


BINARY_OPS: dict[str, Callable[[float, float], float]] = {
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "div": protected_div,
    "min": min,
    "max": max,
}

UNARY_OPS: dict[str, Callable[[float], float]] = {
    "sin": math.sin,
    "cos": math.cos,
    "exp": protected_exp,
    "log": protected_log,
    "neg": operator.neg,
    "sqrt": protected_sqrt,
}

ALLOWED_OP_NAMES: frozenset[str] = frozenset(BINARY_OPS) | frozenset(UNARY_OPS)


def eval_tree(node: Any, env: dict[str, float]) -> float:
    """Evaluate a prefix JSON tree.

    Forms:
      {"var": "x0"}
      {"const": 1.5}
      {"op": "add", "args": [node, node]}
      {"op": "sin", "args": [node]}
    """
    if not isinstance(node, dict):
        raise ValueError("expression node must be an object")
    if "var" in node:
        name = str(node["var"])
        if name not in env:
            raise ValueError(f"unknown variable {name!r}")
        return float(env[name])
    if "const" in node:
        return float(node["const"])
    if "op" in node:
        op = str(node["op"])
        args = node.get("args")
        if not isinstance(args, list):
            raise ValueError("op node requires args list")
        if op in BINARY_OPS:
            if len(args) != 2:
                raise ValueError(f"binary op {op} needs 2 args")
            return float(BINARY_OPS[op](eval_tree(args[0], env), eval_tree(args[1], env)))
        if op in UNARY_OPS:
            if len(args) != 1:
                raise ValueError(f"unary op {op} needs 1 arg")
            return float(UNARY_OPS[op](eval_tree(args[0], env)))
        raise ValueError(f"operator {op!r} not in allow-list")
    raise ValueError("node must contain var, const, or op")


def tree_size(node: Any) -> int:
    if not isinstance(node, dict):
        return 0
    if "op" in node:
        args = node.get("args") or []
        return 1 + sum(tree_size(a) for a in args)
    return 1


def tree_depth(node: Any) -> int:
    if not isinstance(node, dict) or "op" not in node:
        return 1
    args = node.get("args") or []
    if not args:
        return 1
    return 1 + max(tree_depth(a) for a in args)
