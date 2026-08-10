"""neural.transformer.encoder."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.skill_io import train_transformer_from_inputs


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = train_transformer_from_inputs(inputs)
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
            "train_metrics": result["train_metrics"],
            "n_params": result.get("n_params"),
            "capacity": result.get("capacity"),
        },
    }
