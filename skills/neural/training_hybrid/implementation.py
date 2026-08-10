"""ADR 0033 evolutionary neural training skill."""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import NevergradNotAvailableError, PymooNotAvailableError
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.evolutionary_training import hybrid_evolutionary_train


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        seeds = inputs.get("seeds")
        result = hybrid_evolutionary_train(
            inputs["x"],
            inputs["y"],
            max_evaluations=int(inputs.get("max_evaluations", inputs.get("budget", 12))),
            seed=int(inputs.get("seed", 42)),
            seeds=list(seeds) if seeds is not None else None,
            inner_epochs=int(inputs.get("inner_epochs", inputs.get("epochs", 20))),
            device=str(inputs.get("device", "cpu")),
            max_wall_time_s=inputs.get("max_wall_time_s"),
            population_size=int(inputs.get("population_size", 8)),
            max_generations=inputs.get("max_generations"),
            facets=list(inputs.get("facets") or ["hyperparameters", "architecture"]),
            multiobjective=bool(inputs.get("multiobjective", False)),
        )
    except (
        TorchNotAvailableError,
        NevergradNotAvailableError,
        PymooNotAvailableError,
        ValueError,
    ) as exc:
        msg = getattr(exc, "message", str(exc))
        return {
            "result": {"error": {"message": msg}},
            "diagnostics": {"converged": False, "backend": "hybrid", "message": msg},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "hybrid",
            "seed": result.get("seed"),
            "mode": result.get("mode"),
            "n_trials": result.get("n_trials"),
            "best_config": result.get("best_config"),
        },
    }
