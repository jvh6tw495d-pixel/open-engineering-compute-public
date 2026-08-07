"""statistics.regression entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.statistics.regression.linear_regression`` — no algorithm is
reimplemented here (ADR 0008).
"""

from __future__ import annotations

from typing import Any

from oec.kernel.statistics.regression import linear_regression


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    result = linear_regression(inputs["x"], inputs["y"])
    return {
        "result": {
            "coefficients": result.coefficients,
            "fitted": result.fitted,
            "residuals": result.residuals,
            "r_squared": result.r_squared,
            "adj_r_squared": result.adj_r_squared,
            "rmse": result.rmse,
            "residual_standard_error": result.residual_standard_error,
            "n": result.n,
            "k": result.k,
            "backend": result.backend,
        },
        "diagnostics": {
            "n": result.n,
            "k": result.k,
            "r_squared": result.r_squared,
            "rmse": result.rmse,
            "converged": None,
            "backend": result.backend,
        },
    }