"""optimization.infeasibility_explain entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.optimization.feasibility.explain_infeasibility`` — no HiGHS
algorithm is reimplemented here (ADR 0008).
"""

from __future__ import annotations

from typing import Any

from oec.kernel.optimization.feasibility import explain_infeasibility


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if "max_drop_one_solves" in inputs:
        kwargs["max_drop_one_solves"] = int(inputs["max_drop_one_solves"])
    out = explain_infeasibility(inputs["ops"], **kwargs)
    return {
        "result": out,
        "diagnostics": {
            "feasible": out["feasible"],
            "status": out.get("status"),
            "tier": out["tier"],
            "claims_iis": out.get("claims_iis", False),
            "n_constraints": out["n_constraints"],
            "converged": None,
            "backend": out["backend"],
        },
    }