"""hybrid.surrogate_optimize — X2 surrogate + evo + true-f verify."""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import NevergradNotAvailableError
from oec.kernel.hybrid.surrogate import surrogate_then_evolve
from oec.kernel.neural.errors import TorchNotAvailableError


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = surrogate_then_evolve(
            built_in=str(inputs.get("built_in", "sphere")),
            n_var=int(inputs.get("n_var", 2)),
            lower=float(inputs.get("lower", -5.0)),
            upper=float(inputs.get("upper", 5.0)),
            n_train=int(inputs.get("n_train", 60)),
            surrogate_epochs=int(inputs.get("surrogate_epochs", 40)),
            evo_budget=int(inputs.get("evo_budget", 80)),
            optimizer=str(inputs.get("optimizer", "OnePlusOne")),
            seed=int(inputs.get("seed", 42)),
            n_verify=int(inputs.get("n_verify", 5)),
            device=str(inputs.get("device", "cpu")),
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
            "accepted_as_engineering_truth": False,
            "best_true_f": result["high_fidelity"]["best_true"]["true_f"],
        },
    }
