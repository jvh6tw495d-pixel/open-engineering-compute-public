"""ODE IVP via SciPy solve_ivp. Merit: SciPy."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp


def integrate_ivp(
    fun: Callable[[float, Any], Any],
    t_span: tuple[float, float],
    y0: Sequence[float],
    *,
    method: str = "RK45",
    rtol: float = 1e-6,
    atol: float = 1e-9,
    t_eval: Sequence[float] | None = None,
) -> dict[str, Any]:
    y0_arr = np.array(list(y0), dtype=float)
    t_eval_arr = None if t_eval is None else np.array(list(t_eval), dtype=float)

    def wrapped(t: float, y: Any) -> Any:
        return np.asarray(fun(float(t), y), dtype=float)

    sol = solve_ivp(  # type: ignore[call-overload]
        wrapped,
        t_span,
        y0_arr,
        method=method,
        rtol=rtol,
        atol=atol,
        t_eval=t_eval_arr,
        dense_output=False,
    )
    y_t = np.asarray(sol.y.T, dtype=float)
    return {
        "t": [float(v) for v in np.asarray(sol.t, dtype=float).tolist()],
        "y": [[float(v) for v in row] for row in y_t.tolist()],
        "success": bool(sol.success),
        "message": str(sol.message),
        "nfev": int(sol.nfev),
        "method": method,
        "backend": "scipy",
    }
