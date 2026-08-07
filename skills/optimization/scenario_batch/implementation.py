from __future__ import annotations

from typing import Any

from oec.kernel.optimization.feasibility import scenario_batch


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = scenario_batch(
        inputs["ops"],
        path=inputs["path"],
        values=list(inputs["values"]),
    )
    return {
        "result": out,
        "diagnostics": {
            "converged": out["n_optimal"] > 0,
            "n_scenarios": out["n_scenarios"],
            "n_optimal": out["n_optimal"],
        },
    }
