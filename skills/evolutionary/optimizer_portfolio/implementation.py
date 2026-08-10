"""evolutionary.optimizer_portfolio"""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.blackbox import optimizer_portfolio
from oec.kernel.evolutionary.errors import NevergradNotAvailableError


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = optimizer_portfolio(
            built_in=str(inputs.get("built_in", "sphere")),
            n_var=int(inputs.get("n_var", 2)),
            lower=float(inputs.get("lower", -5.0)),
            upper=float(inputs.get("upper", 5.0)),
            budget=int(inputs.get("budget", 80)),
            optimizers=list(
                inputs.get("optimizers") or ["OnePlusOne", "TwoPointsDE", "RandomSearch"]
            ),
            seed=int(inputs.get("seed", 42)),
        )
    except NevergradNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "nevergrad",
            },
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "nevergrad",
            "seed": result["seed"],
            "best_optimizer": result["best_optimizer"],
            "best_objective": result["best_objective"],
        },
    }
