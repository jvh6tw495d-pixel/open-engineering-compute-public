"""optimization.cvar_lp entrypoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.optimization.cvar import cvar_lp


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = cvar_lp(
        decision_vars=list(inputs["decision_vars"]),
        loss_scenarios=list(inputs["loss_scenarios"]),
        alpha=float(inputs["alpha"]),
        structural_constraints=inputs.get("structural_constraints"),
    )
    return {
        "result": out,
        "diagnostics": {
            "converged": out["converged"],
            "alpha": out["alpha"],
            "backend": out["backend"],
            "message": out["solver_status"],
        },
    }
