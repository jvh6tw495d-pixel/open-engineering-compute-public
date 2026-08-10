"""neural.autoencoder.denoising."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.skill_io import train_autoencoder_from_inputs


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        # default noise if not provided
        if "noise_std" not in inputs:
            inputs = {**inputs, "noise_std": 0.1}
        result = train_autoencoder_from_inputs(inputs, default_noise=0.1)
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "backend": "torch"},
        }
    except ValueError as exc:
        return {
            "result": {"error": {"type": "ValueError", "message": str(exc)}},
            "diagnostics": {"converged": False, "message": str(exc), "backend": "torch"},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "torch",
            "seed": result["seed"],
            "mse": result["train_metrics"]["mse"],
            "n_params": result.get("n_params"),
            "capacity": result.get("capacity"),
        },
    }
