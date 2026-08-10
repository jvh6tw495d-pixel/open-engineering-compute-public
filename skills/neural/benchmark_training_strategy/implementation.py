"""neural.benchmark.training_strategy — gradient vs hybrid vs neuroevolution."""

from __future__ import annotations

from typing import Any

from oec.kernel.evolutionary.errors import NevergradNotAvailableError
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.evolutionary_training import benchmark_training_strategies


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        result = benchmark_training_strategies(
            inputs["x"],
            inputs["y"],
            seed=int(inputs.get("seed", 42)),
            max_evaluations=int(inputs.get("max_evaluations", 8)),
            inner_epochs=int(inputs.get("inner_epochs", 12)),
            device=str(inputs.get("device", "cpu")),
        )
    except (TorchNotAvailableError, NevergradNotAvailableError, ValueError) as exc:
        msg = getattr(exc, "message", str(exc))
        return {
            "result": {"error": {"message": msg}},
            "diagnostics": {"converged": False, "backend": "benchmark", "message": msg},
        }
    return {
        "result": result,
        "diagnostics": {
            "converged": True,
            "backend": "benchmark",
            "seed": result.get("seed"),
            "arms": [a.get("strategy") for a in result.get("arms", [])],
        },
    }
