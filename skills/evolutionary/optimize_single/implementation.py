"""evolutionary.optimize_single — dispatch over pymoo algorithms (Part B depth)."""

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
from oec.evolutionary.runtime import EvolutionaryRuntimeSpec
from oec.kernel.evolutionary.errors import PymooNotAvailableError
from oec.kernel.evolutionary.optimize import optimize_single
from oec.kernel.evolutionary.seed_matrix import run_seed_matrix


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    built_in_raw = inputs.get("built_in")
    expression = inputs.get("expression")
    built_in: BuiltInProblemName | None
    if expression is not None:
        built_in = BuiltInProblemName(built_in_raw) if built_in_raw else None
    else:
        built_in = BuiltInProblemName(built_in_raw or "sphere")

    problem = EvolutionaryProblemSpec(
        variables=[VariableSpec(**v) for v in inputs["variables"]],
        sense=inputs.get("sense", "min"),
        built_in=built_in,
        expression=expression,
        constraints=list(inputs.get("constraints") or []),
    )
    budget = BudgetSpec(
        generations=int(inputs.get("generations", 40)),
        population=int(inputs.get("population", 30)),
    )
    algorithm = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName(inputs.get("algorithm", "differential_evolution")),
        budget=budget,
        seed=int(inputs.get("seed", 42)),
    )
    seeds = inputs.get("seeds")
    runtime = EvolutionaryRuntimeSpec(
        seed=int(inputs.get("seed", 42)),
        seeds=list(seeds) if seeds is not None else None,
        budget=budget,
        max_seconds=inputs.get("max_seconds"),
        max_evaluations=inputs.get("max_evaluations"),
        history=bool(inputs.get("history", True)),
    )
    try:
        if seeds is not None and len(seeds) > 1:
            report = run_seed_matrix(problem, algorithm, runtime)
            payload = report.model_dump(mode="json")
            return {
                "result": payload,
                "diagnostics": {
                    "converged": True,
                    "message": report.message,
                    "backend": "pymoo",
                    "mode": "multi_seed",
                    "mean_best_objective": report.mean_best_objective,
                    "std_best_objective": report.std_best_objective,
                    "seeds": report.seeds,
                },
            }
        result = optimize_single(problem, algorithm, runtime=runtime)
    except PymooNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "pymoo",
            },
        }
    except (ValueError, RuntimeError) as exc:
        return {
            "result": {"error": {"type": type(exc).__name__, "message": str(exc)}},
            "diagnostics": {
                "converged": False,
                "message": str(exc),
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
            "objective_mode": result.objective_mode,
            "n_constraints": result.n_constraints,
        },
    }
