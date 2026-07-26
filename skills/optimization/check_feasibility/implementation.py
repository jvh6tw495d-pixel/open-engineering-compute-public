from __future__ import annotations

from typing import Any

from oec.kernel.optimization.feasibility import check_feasibility


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = check_feasibility(inputs["ops"])
    return {
        "result": out,
        "diagnostics": {
            "converged": bool(out.get("feasible")),
            "feasible": out.get("feasible"),
            "message": "; ".join(out.get("feasibility_issues") or []) or "ok",
        },
    }
