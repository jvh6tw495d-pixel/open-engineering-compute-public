"""neural.gcn."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.gnn import train_gnn


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = train_gnn(
            inputs["node_features"],
            inputs["edge_index"],
            inputs["y"],
            train_mask=inputs.get("train_mask"),
            arch="gcn",
            task=str(inputs.get("task", "regression")),
            n_classes=int(inputs.get("n_classes", 1)),
            hidden=int(inputs.get("hidden", 16)),
            n_layers=int(inputs.get("n_layers", 2)),
            heads=int(inputs.get("heads", 2)),
            epochs=int(inputs.get("epochs", 40)),
            lr=float(inputs.get("lr", 1e-2)),
            seed=int(inputs.get("seed", 42)),
            device=str(inputs.get("device", "cpu")),
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
