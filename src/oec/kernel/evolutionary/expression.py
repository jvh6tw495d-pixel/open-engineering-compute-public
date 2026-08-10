"""Evaluate closed expression / constraint IR for evolutionary problems (E-D2/E-D3).

Reuses GP operator allow-list — no eval/exec.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.evolutionary.gp_operators import eval_tree


def env_from_vector(variable_names: list[str], x: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, dtype=float).reshape(-1)
    if len(variable_names) != x.size:
        raise ValueError(f"x has {x.size} dims but problem has {len(variable_names)} variables")
    return {name: float(x[i]) for i, name in enumerate(variable_names)}


def evaluate_expression(tree: dict[str, Any], variable_names: list[str], x: np.ndarray) -> float:
    """Evaluate a closed IR tree at decision vector ``x``."""
    env = env_from_vector(variable_names, x)
    return float(eval_tree(tree, env))


def evaluate_constraints(
    constraints: list[Any],
    variable_names: list[str],
    x: np.ndarray,
) -> list[float]:
    """Return g values for each constraint (feasible when all g ≤ 0)."""
    env = env_from_vector(variable_names, x)
    out: list[float] = []
    for c in constraints:
        tree = c.tree if hasattr(c, "tree") else c["tree"]
        out.append(float(eval_tree(tree, env)))
    return out
