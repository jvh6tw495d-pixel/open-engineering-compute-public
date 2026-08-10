"""evolutionary.evolution_strategy"""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import DeapNotAvailableError
from oec.kernel.evolutionary.gp import run_evolution_strategy


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = run_evolution_strategy(
            n_var=int(inputs.get("n_var", 2)),
            built_in=str(inputs.get("built_in", "sphere")),
            population=int(inputs.get("population", 30)),
            generations=int(inputs.get("generations", 25)),
            seed=int(inputs.get("seed", 42)),
            sigma=float(inputs.get("sigma", 0.5)),
        )
    except DeapNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "backend": "deap"},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "deap",
            "seed": result["seed"],
            "best_objective": result["best_objective"],
        },
    }
