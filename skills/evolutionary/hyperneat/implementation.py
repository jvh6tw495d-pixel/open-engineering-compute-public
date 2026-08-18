"""evolutionary.hyperneat — CPPN + fixed substrate (ADR 0045)."""

from __future__ import annotations

from typing import Any

from oec.evolutionary.contracts import (
    HyperNeatAlgorithmSpec,
    HyperNeatSubstrateName,
    NeatFitnessName,
    NeatProblemSpec,
)
from oec.kernel.evolutionary.errors import NeatNotAvailableError
from oec.kernel.evolutionary.hyperneat import run_hyperneat


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        problem = NeatProblemSpec(
            fitness=NeatFitnessName(inputs["fitness"]),
            x=inputs.get("x"),
            y=inputs.get("y"),
        )
        algorithm = HyperNeatAlgorithmSpec(
            generations=int(inputs.get("generations", 30)),
            population=int(inputs.get("population", 50)),
            seed=int(inputs.get("seed", 42)),
            substrate=HyperNeatSubstrateName(inputs.get("substrate", "layered_1d")),
            hidden_layers=int(inputs.get("hidden_layers", 1)),
            hidden_width=int(inputs.get("hidden_width", 3)),
            weight_threshold=float(inputs.get("weight_threshold", 0.2)),
            feed_forward=bool(inputs.get("feed_forward", True)),
        )
        result = run_hyperneat(problem, algorithm)
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
            "diagnostics": {
                "converged": False,
                "message": str(exc),
                "backend": "neat-python",
            },
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
            "n_substrate_connections": result.n_substrate_connections,
        },
    }
