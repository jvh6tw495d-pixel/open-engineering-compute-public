"""optimization.infeasibility_explain entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.optimization.feasibility.explain_infeasibility`` — no HiGHS
algorithm is reimplemented here (ADR 0008).
"""

from __future__ import annotations

from typing import Any

from oec.kernel.optimization.feasibility import explain_infeasibility


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = explain_infeasibility(inputs["ops"])
    return {
        "result": out,
        "diagnostics": {
            "feasible": out["feasible"],
            "tier": out["tier"],
            "n_constraints": out["n_constraints"],
            "converged": None,
            "backend": out["backend"],
        },
    }