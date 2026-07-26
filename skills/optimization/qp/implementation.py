from __future__ import annotations

from typing import Any

from oec.kernel.optimization.qp import solve_qp


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = solve_qp(
        inputs["Q"],
        inputs["c"],
        x0=inputs.get("x0"),
        bounds=inputs.get("bounds"),
        a_ub=inputs.get("A_ub"),
        b_ub=inputs.get("b_ub"),
        a_eq=inputs.get("A_eq"),
        b_eq=inputs.get("b_eq"),
        sense=inputs.get("sense", "min"),
    )
    return {
        "result": out,
        "diagnostics": {
            "converged": bool(out.get("success")),
            "message": out.get("message", ""),
            "nit": out.get("nit"),
        },
    }
