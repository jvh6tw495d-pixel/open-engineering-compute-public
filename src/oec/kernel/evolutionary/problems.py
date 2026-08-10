"""Built-in test problems (E1.0) — no user Python."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from oec.evolutionary.contracts import BuiltInProblemName


def evaluate_built_in(name: BuiltInProblemName, x: np.ndarray) -> float:
    """Return objective value (always minimize form)."""
    x = np.asarray(x, dtype=float).reshape(-1)
    if name == BuiltInProblemName.SPHERE:
        return float(np.sum(x**2))
    if name == BuiltInProblemName.ROSENBROCK:
        if x.size < 2:
            return float(np.sum(x**2))
        total = 0.0
        for i in range(x.size - 1):
            total += 100.0 * (x[i + 1] - x[i] ** 2) ** 2 + (1.0 - x[i]) ** 2
        return float(total)
    if name == BuiltInProblemName.RASTRIGIN:
        n = x.size
        return float(10.0 * n + np.sum(x**2 - 10.0 * np.cos(2.0 * math.pi * x)))
    raise ValueError(f"unknown built-in problem {name}")


def as_callable(name: BuiltInProblemName) -> Callable[[np.ndarray], float]:
    return lambda x: evaluate_built_in(name, x)
