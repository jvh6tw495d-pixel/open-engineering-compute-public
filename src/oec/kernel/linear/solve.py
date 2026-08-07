"""Dense linear solve Ax=b (NumPy). Merit: NumPy/LAPACK."""

from __future__ import annotations

from typing import Any

import numpy as np


def solve_dense(a: list[list[float]], b: list[float]) -> dict[str, Any]:
    matrix: Any = np.array(a, dtype=float)
    rhs: Any = np.array(b, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("A must be a square 2-D matrix")
    if rhs.ndim != 1 or rhs.shape[0] != matrix.shape[0]:
        raise ValueError("b must be a 1-D vector with len(b) == n for A (n x n)")
    cond = float(np.linalg.cond(matrix))
    try:
        x: Any = np.linalg.solve(matrix, rhs)
        residual: Any = matrix @ x - rhs
        return {
            "x": [float(v) for v in list(x)],
            "residual_norm": float(np.linalg.norm(residual, ord=2)),
            "condition_number": cond,
            "singular": False,
            "backend": "numpy",
        }
    except np.linalg.LinAlgError:
        return {
            "x": [],
            "residual_norm": None,
            "condition_number": cond,
            "singular": True,
            "backend": "numpy",
        }
