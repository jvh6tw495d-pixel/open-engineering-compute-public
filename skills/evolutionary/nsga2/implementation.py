"""evolutionary.nsga2 — multi-objective via pymoo."""

from __future__ import annotations

from typing import Any

from oec.evolutionary.contracts import (
    BudgetSpec,
    BuiltInMultiProblemName,
    MultiObjectiveAlgorithmName,
    MultiObjectiveAlgorithmSpec,
    MultiObjectiveProblemSpec,
    VariableSpec,
)
from oec.kernel.evolutionary.errors import PymooNotAvailableError
from oec.kernel.evolutionary.multiobjective import optimize_multi


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    problem = MultiObjectiveProblemSpec(
        variables=[VariableSpec(**v) for v in inputs["variables"]],
        built_in=BuiltInMultiProblemName(inputs.get("built_in", "zdt1")),
        n_objectives=2,
    )
    algorithm = MultiObjectiveAlgorithmSpec(
        algorithm=MultiObjectiveAlgorithmName("nsga2"),
        budget=BudgetSpec(
            generations=int(inputs.get("generations", 30)),
            population=int(inputs.get("population", 40)),
        ),
        seed=int(inputs.get("seed", 42)),
        n_partitions=int(inputs.get("n_partitions", 12)),
    )
    try:
        result = optimize_multi(problem, algorithm)
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
            "converged": result.n_nondominated > 0,
            "message": result.message,
            "backend": "pymoo",
            "seed": result.seed,
            "n_nondominated": result.n_nondominated,
            "hypervolume": result.hypervolume,
        },
    }
