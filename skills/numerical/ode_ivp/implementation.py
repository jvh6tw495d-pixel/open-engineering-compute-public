"""numerical.ode_ivp — y' = f(t,y) via SciPy solve_ivp."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.numerics.expressions import compile_expression_vector
from oec.kernel.numerics.ode import integrate_ivp


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    state = list(inputs["state_names"])
    symbols = tuple(["t", *state])
    compiled = [compile_expression_vector(eq, symbols=symbols) for eq in inputs["dydt_expressions"]]

    def fun(t: float, y: np.ndarray) -> np.ndarray:
        vals = [float(t), *[float(v) for v in y]]
        return np.asarray([float(f(vals)) for f in compiled], dtype=float)

    out = integrate_ivp(
        fun,
        (float(inputs["t_span"][0]), float(inputs["t_span"][1])),
        list(inputs["y0"]),
        method=inputs.get("method", "RK45"),
        rtol=float(inputs.get("rtol", 1e-6)),
        atol=float(inputs.get("atol", 1e-9)),
        t_eval=inputs.get("t_eval"),
    )
    return {
        "result": out,
        "diagnostics": {
            "converged": bool(out["success"]),
            "message": out["message"],
            "n_function_evaluations": out["nfev"],
        },
    }
