"""ODE initial-value problems via SciPy's ``solve_ivp`` — unified under
``kernel/computational`` (ADR 0022). Moved from ``kernel/numerics/ode.py``;
logic unchanged, only the return type differs.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict
from scipy.integrate import solve_ivp

from oec.kernel.computational.diagnostics import ComputationalDiagnostics


class ODEResult(BaseModel):
    """An ODE initial-value problem's solved trajectory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    t: list[float]
    y: list[list[float]]
    diagnostics: ComputationalDiagnostics


def integrate_ivp(
    fun: Callable[[float, Any], Any],
    t_span: tuple[float, float],
    y0: Sequence[float],
    *,
    method: str = "RK45",
    rtol: float = 1e-6,
    atol: float = 1e-9,
    t_eval: Sequence[float] | None = None,
) -> ODEResult:
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

    return ODEResult(
        t=[float(v) for v in np.asarray(sol.t, dtype=float).tolist()],
        y=[[float(v) for v in row] for row in y_t.tolist()],
        diagnostics=ComputationalDiagnostics(
            method=method,
            backend="scipy",
            converged=bool(sol.success),
            function_calls=int(sol.nfev),
            message=str(sol.message),
        ),
    )
