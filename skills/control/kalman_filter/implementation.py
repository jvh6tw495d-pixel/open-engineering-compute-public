"""control.kalman_filter entrypoint."""
from __future__ import annotations

from typing import Any

from oec.kernel.control.kalman import kalman_filter_linear


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = kalman_filter_linear(
        inputs["A"],
        inputs.get("B"),
        inputs["C"],
        inputs["Q"],
        inputs["R"],
        inputs["z"],
        inputs["x0"],
        inputs["P0"],
        u=inputs.get("u"),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_steps": out["n_steps"],
            "converged": None,
            "backend": out["backend"],
        },
    }
