from __future__ import annotations

from typing import Any

from oec.kernel.statistics.monte_carlo import monte_carlo_mean


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = monte_carlo_mean(
        inputs["expression"],
        n_samples=int(inputs["n_samples"]),
        low=float(inputs["low"]),
        high=float(inputs["high"]),
        seed=inputs.get("seed"),
        symbol=inputs.get("symbol", "x"),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_samples": out["n_samples"],
            "stderr": out["stderr"],
            "seed": out["seed"],
        },
    }
