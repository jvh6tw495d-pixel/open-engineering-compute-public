"""numerical.ode_ivp — y' = f(t,y) via SciPy solve_ivp."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.computational.ode import integrate_ivp
from oec.kernel.numerics.expressions import compile_expression_vector


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    state = list(inputs["state_names"])
    symbols = tuple(["t", *state])
    compiled = [compile_expression_vector(eq, symbols=symbols) for eq in inputs["dydt_expressions"]]

    def fun(t: float, y: np.ndarray) -> np.ndarray:
        vals = [float(t), *[float(v) for v in y]]
        return np.asarray([float(f(vals)) for f in compiled], dtype=float)

    result = integrate_ivp(
        fun,
        (float(inputs["t_span"][0]), float(inputs["t_span"][1])),
        list(inputs["y0"]),
        method=inputs.get("method", "RK45"),
        rtol=float(inputs.get("rtol", 1e-6)),
        atol=float(inputs.get("atol", 1e-9)),
        t_eval=inputs.get("t_eval"),
    )
    diag = result.diagnostics.model_dump()
    return {
        "result": {
            "t": result.t,
            "y": result.y,
            "success": diag["converged"],
            "message": diag["message"],
            "nfev": diag["function_calls"],
            "method": diag["method"],
            "backend": diag["backend"],
        },
        "diagnostics": {
            "converged": bool(diag["converged"]),
            "message": diag["message"],
            "n_function_evaluations": diag["function_calls"],
        },
    }
