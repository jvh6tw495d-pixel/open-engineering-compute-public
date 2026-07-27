"""linear.least_squares entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.linear.analysis.least_squares`` — no LAPACK code is
reimplemented here.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.linear.analysis import least_squares


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = least_squares(inputs["A"], inputs["b"])
    return {
        "result": {
            "solution": out["solution"],
            "residuals": out["residuals"],
            "rank": out["rank"],
            "singular_values": out["singular_values"],
            "residual_sum_of_squares": out["residual_sum_of_squares"],
            "backend": out["backend"],
            "converged": out["converged"],
        },
        "diagnostics": {
            "rank": out["rank"],
            "n_singular_values": len(out["singular_values"]),
            "residual_sum_of_squares": out["residual_sum_of_squares"],
            "converged": out["converged"],
            "backend": out["backend"],
        },
    }