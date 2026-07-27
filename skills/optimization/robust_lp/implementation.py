"""optimization.robust_lp entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.optimization.robust import robust_lp_box_rhs


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = robust_lp_box_rhs(
        inputs["ops"],
        rhs_uncertainty={
            str(k): float(v) for k, v in dict(inputs["rhs_uncertainty"]).items()
        },
    )
    return {
        "result": out,
        "diagnostics": {
            "converged": out["converged"],
            "backend": out["backend"],
            "message": out["solver_status"],
        },
    }
