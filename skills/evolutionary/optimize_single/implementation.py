"""evolutionary.optimize_single — dispatch over pymoo algorithms."""

from __future__ import annotations

from typing import Any

from oec.evolutionary.contracts import (
    AlgorithmName,
    BudgetSpec,
    BuiltInProblemName,
    EvolutionaryAlgorithmSpec,
    EvolutionaryProblemSpec,
    VariableSpec,
)
from oec.kernel.evolutionary.errors import PymooNotAvailableError
from oec.kernel.evolutionary.optimize import optimize_single


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    problem = EvolutionaryProblemSpec(
        variables=[VariableSpec(**v) for v in inputs["variables"]],
        sense=inputs.get("sense", "min"),
        built_in=BuiltInProblemName(inputs.get("built_in", "sphere")),
    )
    algorithm = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName(inputs.get("algorithm", "differential_evolution")),
        budget=BudgetSpec(
            generations=int(inputs.get("generations", 40)),
            population=int(inputs.get("population", 30)),
        ),
        seed=int(inputs.get("seed", 42)),
    )
    try:
        result = optimize_single(problem, algorithm)
    except PymooNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "pymoo",
            },
        }
    payload = result.model_dump(mode="json")
    return {
        "result": payload,
        "diagnostics": {
            "converged": True,
            "message": result.message,
            "backend": "pymoo",
            "seed": result.seed,
            "best_objective": result.best_objective,
        },
    }
