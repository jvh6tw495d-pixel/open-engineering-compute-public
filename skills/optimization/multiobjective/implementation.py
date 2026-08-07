from __future__ import annotations

from typing import Any

from oec.kernel.optimization.multiobjective import weighted_sum_lp


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = weighted_sum_lp(
        inputs["ops"],
        objectives=inputs["objectives"],
        weights=inputs["weights"],
    )
    return {
        "result": out,
        "diagnostics": {
            "converged": bool(out.get("success")),
            "method": "weighted_sum",
            "message": out.get("solver_status", ""),
        },
    }
