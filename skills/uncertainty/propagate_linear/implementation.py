"""uncertainty.propagate_linear entrypoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.uncertainty.propagate import propagate_linear


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = propagate_linear(
        inputs["jacobian"],
        inputs["covariance"],
        nominal=inputs.get("nominal"),
    )
    return {
        "result": out,
        "diagnostics": {
            "output_dim": out["output_dim"],
            "converged": None,
            "backend": out["backend"],
        },
    }
