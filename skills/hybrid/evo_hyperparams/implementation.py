"""hybrid.evo_hyperparams — Nevergrad over closed MLP hyperparam catalog."""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import NevergradNotAvailableError
from oec.kernel.hybrid.hyperparams import evo_hyperparameter_search
from oec.kernel.neural.errors import TorchNotAvailableError


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = evo_hyperparameter_search(
            inputs["x"],
            inputs["y"],
            budget=int(inputs.get("budget", 8)),
            seed=int(inputs.get("seed", 42)),
            epochs=int(inputs.get("epochs", 20)),
            device=str(inputs.get("device", "cpu")),
            task=str(inputs.get("task", "regression")),
        )
    except (TorchNotAvailableError, NevergradNotAvailableError) as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "hybrid",
            },
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "hybrid",
            "seed": result["seed"],
            "best_config": result["best_config"],
            "n_trials": result["n_trials"],
        },
    }
