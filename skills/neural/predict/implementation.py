"""neural.predict — forward pass from a training checkpoint payload."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import predict_mlp


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"device": str(inputs.get("device", "cpu"))}
    if "normalize" in inputs:
        kwargs["normalize"] = inputs["normalize"]
    try:
        # normalize omitted entirely (not passed as None) so predict_mlp falls
        # back to the checkpoint's own normalize state instead of silently
        # skipping normalization.
        preds = predict_mlp(inputs["x"], inputs["checkpoint"], **kwargs)
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": None, "message": exc.message, "backend": "torch"},
        }
    return {
        "result": {"predictions": preds, "backend": "torch"},
        "diagnostics": {"converged": None, "backend": "torch", "n": len(inputs["x"])},
    }
