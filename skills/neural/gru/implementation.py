"""neural.gru."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.sequences import train_sequence_model


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = train_sequence_model(
            inputs["x"],
            inputs["y"],
            arch="gru",
            task=str(inputs.get("task", "regression")),
            n_classes=int(inputs.get("n_classes", 1)),
            hidden=int(inputs.get("hidden", 32)),
            n_layers=int(inputs.get("n_layers", 1)),
            epochs=int(inputs.get("epochs", 30)),
            batch_size=int(inputs.get("batch_size", 8)),
            lr=float(inputs.get("lr", 1e-3)),
            seed=int(inputs.get("seed", 42)),
            device=str(inputs.get("device", "cpu")),
            kernel_size=int(inputs.get("kernel_size", 3)),
            dropout=float(inputs.get("dropout", 0.0)),
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
            "train_metrics": result["train_metrics"],
        },
    }
