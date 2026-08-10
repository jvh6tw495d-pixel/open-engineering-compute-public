"""evolutionary.benchmark — X1 thin controlled comparison harness."""

from __future__ import annotations

from typing import Any

from oec.evolutionary.contracts import (
    AlgorithmName,
    BenchmarkSpec,
    BuiltInMultiProblemName,
    BuiltInProblemName,
    MultiObjectiveAlgorithmName,
    VariableSpec,
)
from oec.kernel.evolutionary.benchmark import run_benchmark
from oec.kernel.evolutionary.errors import PymooNotAvailableError


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    mode = inputs.get("mode", "single")
    variables = [VariableSpec(**v) for v in inputs["variables"]]
    seeds = list(inputs.get("seeds") or [0, 1, 2])
    generations = int(inputs.get("generations", 15))
    population = int(inputs.get("population", 20))

    if mode == "single":
        algos = [
            AlgorithmName(a)
            for a in (inputs.get("algorithms") or ["differential_evolution", "genetic_algorithm"])
        ]
        built_in = BuiltInProblemName(inputs.get("built_in", "sphere"))
        spec = BenchmarkSpec(
            mode="single",
            built_in=built_in,
            algorithms=algos,
            variables=variables,
            generations=generations,
            population=population,
            seeds=seeds,
        )
    else:
        multi_algos = [
            MultiObjectiveAlgorithmName(a)
            for a in (inputs.get("multi_algorithms") or ["nsga2", "nsga3"])
        ]
        multi_built_in = BuiltInMultiProblemName(inputs.get("multi_built_in", "zdt1"))
        spec = BenchmarkSpec(
            mode="multi",
            multi_built_in=multi_built_in,
            multi_algorithms=multi_algos,
            variables=variables,
            generations=generations,
            population=population,
            seeds=seeds,
        )

    try:
        result = run_benchmark(spec)
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
            "n_rows": len(result.rows),
            "best_mean_algorithm": result.summary.get("best_mean_algorithm"),
        },
    }
