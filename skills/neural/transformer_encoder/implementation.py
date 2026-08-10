"""neural.transformer.encoder."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.transformer import train_transformer_sequence


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = train_transformer_sequence(
            inputs["x"],
            inputs["y"],
            task=str(inputs.get("task", "regression")),
            n_classes=int(inputs.get("n_classes", 1)),
            d_model=int(inputs.get("d_model", 32)),
            n_heads=int(inputs.get("n_heads", 4)),
            n_layers=int(inputs.get("n_layers", 2)),
            ff_dim=int(inputs.get("ff_dim", 64)),
            dropout=float(inputs.get("dropout", 0.0)),
            epochs=int(inputs.get("epochs", 25)),
            batch_size=int(inputs.get("batch_size", 8)),
            lr=float(inputs.get("lr", 1e-3)),
            seed=int(inputs.get("seed", 42)),
            device=str(inputs.get("device", "cpu")),
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
