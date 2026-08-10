"""neural.evaluate — metrics on held-out data given a checkpoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import evaluate_mlp
from oec.neural.contracts import NeuralTask


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    task = NeuralTask(inputs.get("task", "regression"))
    try:
        result = evaluate_mlp(
            inputs["x"],
            inputs["y"],
            inputs["checkpoint"],
            task=task,
            normalize=inputs.get("normalize"),
            device=str(inputs.get("device", "cpu")),
        )
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
