"""evolutionary.neat — governed topology evolution (ADR 0044)."""

from __future__ import annotations

from typing import Any

from oec.evolutionary.contracts import NeatAlgorithmSpec, NeatFitnessName, NeatProblemSpec
from oec.kernel.evolutionary.errors import NeatNotAvailableError
from oec.kernel.evolutionary.neat import run_neat


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        problem = NeatProblemSpec(
            fitness=NeatFitnessName(inputs["fitness"]),
            x=inputs.get("x"),
            y=inputs.get("y"),
        )
        algorithm = NeatAlgorithmSpec(
            generations=int(inputs.get("generations", 30)),
            population=int(inputs.get("population", 50)),
            seed=int(inputs.get("seed", 42)),
            compatibility_threshold=float(inputs.get("compatibility_threshold", 3.0)),
            conn_add_prob=float(inputs.get("conn_add_prob", 0.5)),
            node_add_prob=float(inputs.get("node_add_prob", 0.2)),
            num_hidden=int(inputs.get("num_hidden", 0)),
            elitism=int(inputs.get("elitism", 2)),
            feed_forward=bool(inputs.get("feed_forward", True)),
        )
        result = run_neat(problem, algorithm)
    except NeatNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "neat-python",
            },
        }
    except ValueError as exc:
        return {
            "result": {"error": {"message": str(exc)}},
            "diagnostics": {"converged": False, "message": str(exc), "backend": "neat-python"},
        }
    payload = result.model_dump(mode="json")
    return {
        "result": payload,
        "diagnostics": {
            "converged": True,
            "message": result.message,
            "backend": "neat-python",
            "seed": result.seed,
            "best_fitness": result.best_fitness,
            "n_nodes": result.n_nodes,
        },
    }
