"""numerical.root_system — multi-variable f(x)=0 via SciPy root."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.numerics.expressions import compile_expression_vector
from oec.kernel.numerics.root_system import solve_root_system


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    variables = list(inputs["variables"])
    equations = list(inputs["equations"])
    x0 = list(inputs["x0"])
    symbols = tuple(variables)
    compiled = [compile_expression_vector(eq, symbols=symbols) for eq in equations]

    def fun(x: np.ndarray) -> np.ndarray:
        vals = [float(v) for v in x]
        return np.asarray([float(f(vals)) for f in compiled], dtype=float)

    out = solve_root_system(fun, x0, method=inputs.get("method", "hybr"))
    return {
        "result": out,
        "diagnostics": {
            "converged": bool(out["success"]),
            "message": out["message"],
            "n_function_evaluations": out["nfev"],
            "residual": out["residual_norm"],
        },
    }
