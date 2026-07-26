"""Nonlinear systems f(x)=0 via SciPy root. Merit: SciPy."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from scipy.optimize import root


def solve_root_system(
    fun: Callable[[Any], Any],
    x0: Sequence[float],
    *,
    method: str = "hybr",
    tol: float = 1.49012e-08,
) -> dict[str, Any]:
    x0_arr = np.array(list(x0), dtype=float)

    def wrapped(x: Any) -> Any:
        return np.asarray(fun(x), dtype=float)

    sol = root(wrapped, x0_arr, method=method, tol=tol)  # type: ignore[call-overload]
    residual = np.asarray(fun(sol.x), dtype=float)
    return {
        "x": [float(v) for v in np.asarray(sol.x, dtype=float).tolist()],
        "success": bool(sol.success),
        "message": str(sol.message),
        "residual_norm": float(np.linalg.norm(residual, ord=2)),
        "nfev": int(getattr(sol, "nfev", 0) or 0),
        "method": method,
        "backend": "scipy",
    }
