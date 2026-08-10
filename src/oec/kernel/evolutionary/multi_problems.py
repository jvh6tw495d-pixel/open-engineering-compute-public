"""Built-in multi-objective test problems (E2) — no user Python."""

from __future__ import annotations

import math

import numpy as np

from oec.evolutionary.contracts import BuiltInMultiProblemName


def evaluate_multi(name: BuiltInMultiProblemName, x: np.ndarray) -> np.ndarray:
    """Return objective vector (all minimized)."""
    x = np.asarray(x, dtype=float).reshape(-1)
    if name == BuiltInMultiProblemName.BI_SPHERE:
        f1 = float(np.sum(x**2))
        f2 = float(np.sum((x - 1.0) ** 2))
        return np.array([f1, f2], dtype=float)
    if name == BuiltInMultiProblemName.ZDT1:
        return _zdt1(x)
    if name == BuiltInMultiProblemName.ZDT2:
        return _zdt2(x)
    raise ValueError(f"unknown multi-objective built-in {name}")


def _zdt1(x: np.ndarray) -> np.ndarray:
    n = x.size
    f1 = float(x[0])
    g = 1.0 if n == 1 else 1.0 + 9.0 * float(np.sum(x[1:])) / (n - 1)
    f2 = g * (1.0 - math.sqrt(max(f1 / g, 0.0)))
    return np.array([f1, f2], dtype=float)


def _zdt2(x: np.ndarray) -> np.ndarray:
    n = x.size
    f1 = float(x[0])
    g = 1.0 if n == 1 else 1.0 + 9.0 * float(np.sum(x[1:])) / (n - 1)
    f2 = g * (1.0 - (f1 / g) ** 2)
    return np.array([f1, f2], dtype=float)
