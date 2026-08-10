"""neural.predict — forward pass from a training checkpoint payload."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import predict_mlp


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        preds = predict_mlp(
            inputs["x"],
            inputs["checkpoint"],
            normalize=inputs.get("normalize"),
            device=str(inputs.get("device", "cpu")),
        )
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": None, "message": exc.message, "backend": "torch"},
        }
    return {
        "result": {"predictions": preds, "backend": "torch"},
        "diagnostics": {"converged": None, "backend": "torch", "n": len(inputs["x"])},
    }
