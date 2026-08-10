"""evolutionary.genetic_programming"""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import DeapNotAvailableError
from oec.kernel.evolutionary.gp import run_genetic_programming


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = run_genetic_programming(
            n_var=int(inputs.get("n_var", 1)),
            target=str(inputs.get("target", "poly2")),
            n_samples=int(inputs.get("n_samples", 40)),
            population=int(inputs.get("population", 60)),
            generations=int(inputs.get("generations", 20)),
            max_depth=int(inputs.get("max_depth", 5)),
            max_size=int(inputs.get("max_size", 40)),
            seed=int(inputs.get("seed", 42)),
        )
    except DeapNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "backend": "deap"},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": result["best_mse"] < 1e5,
            "backend": "deap",
            "seed": result["seed"],
            "best_mse": result["best_mse"],
        },
    }
