"""numerical.root_system — multi-variable f(x)=0 via SciPy root."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.computational.roots import solve_root_system
from oec.kernel.numerics.expressions import compile_expression_vector


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    variables = list(inputs["variables"])
    equations = list(inputs["equations"])
    x0 = list(inputs["x0"])
    symbols = tuple(variables)
    compiled = [compile_expression_vector(eq, symbols=symbols) for eq in equations]

    def fun(x: np.ndarray) -> np.ndarray:
        vals = [float(v) for v in x]
        return np.asarray([float(f(vals)) for f in compiled], dtype=float)

    result = solve_root_system(fun, x0, method=inputs.get("method", "hybr"))
    diag = result.diagnostics.model_dump()
    return {
        "result": {
            "x": result.x,
            "success": diag["converged"],
            "message": diag["message"],
            "residual_norm": diag["residual"],
            "nfev": diag["function_calls"],
            "method": diag["method"],
            "backend": diag["backend"],
        },
        "diagnostics": {
            "converged": bool(diag["converged"]),
            "message": diag["message"],
            "n_function_evaluations": diag["function_calls"],
            "residual": diag["residual"],
        },
    }
