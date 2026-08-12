"""statistics.distribution_eval — SciPy closed-catalog distribution ops."""

from __future__ import annotations

from typing import Any

from oec.kernel.statistics.distributions import evaluate_distribution


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = evaluate_distribution(
        distribution=str(inputs["distribution"]),
        operation=str(inputs["operation"]),
        params=inputs.get("params"),
        x=inputs.get("x"),
        p=inputs.get("p"),
        n_samples=int(inputs.get("n_samples", 1)),
        seed=inputs.get("seed"),
    )
    return {
        "result": out,
        "diagnostics": {
            "distribution": out["distribution"],
            "operation": out["operation"],
            "backend": out["backend"],
        },
    }
