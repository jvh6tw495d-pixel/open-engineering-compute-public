"""neural.evaluate — metrics on held-out data given a checkpoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import evaluate_mlp
from oec.neural.contracts import NeuralTask


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    task = NeuralTask(inputs.get("task", "regression"))
    kwargs: dict[str, Any] = {"device": str(inputs.get("device", "cpu"))}
    if "normalize" in inputs:
        kwargs["normalize"] = inputs["normalize"]
    try:
        # normalize omitted entirely (not passed as None) so evaluate_mlp falls
        # back to the checkpoint's own normalize state instead of silently
        # skipping normalization.
        result = evaluate_mlp(inputs["x"], inputs["y"], inputs["checkpoint"], task=task, **kwargs)
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": None, "message": exc.message, "backend": "torch"},
        }
    payload = result.model_dump(mode="json")
    return {
        "result": payload,
        "diagnostics": {
            "converged": None,
            "backend": "torch",
            "metrics": result.metrics,
        },
    }
