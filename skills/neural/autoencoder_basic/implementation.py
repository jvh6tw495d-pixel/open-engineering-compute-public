"""neural.autoencoder.basic."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.autoencoder import train_autoencoder
from oec.kernel.neural.errors import TorchNotAvailableError


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = train_autoencoder(
            inputs["x"],
            latent_dim=int(inputs.get("latent_dim", 8)),
            hidden_dims=list(inputs.get("hidden_dims") or [32, 16]),
            epochs=int(inputs.get("epochs", 40)),
            batch_size=int(inputs.get("batch_size", 16)),
            lr=float(inputs.get("lr", 1e-3)),
            seed=int(inputs.get("seed", 42)),
            device=str(inputs.get("device", "cpu")),
            noise_std=float(inputs.get("noise_std", 0.0)),
            activation=str(inputs.get("activation", "relu")),
        )
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "backend": "torch"},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "torch",
            "seed": result["seed"],
            "mse": result["train_metrics"]["mse"],
        },
    }
