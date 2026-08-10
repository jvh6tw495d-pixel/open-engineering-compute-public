"""neural.training.neuroevolution — direct weight evo for small MLPs (ADR 0033 W4)."""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import NevergradNotAvailableError
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.evolutionary_training import neuroevolution_train


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = neuroevolution_train(
            inputs["x"],
            inputs["y"],
            max_evaluations=int(inputs.get("max_evaluations", 40)),
            seed=int(inputs.get("seed", 42)),
            hidden=int(inputs.get("hidden", 8)),
            max_params=int(inputs.get("max_params", 500)),
            device=str(inputs.get("device", "cpu")),
        )
    except (TorchNotAvailableError, NevergradNotAvailableError, ValueError) as exc:
        msg = getattr(exc, "message", str(exc))
        return {
            "result": {"error": {"message": msg}},
            "diagnostics": {"converged": False, "backend": "neuroevolution", "message": msg},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "neuroevolution",
            "seed": result.get("seed"),
            "best_mse": result.get("best_mse"),
            "n_params": result.get("n_params"),
        },
    }
