"""uncertainty.morris entrypoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.uncertainty.morris import morris_screen


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = morris_screen(
        inputs["bounds"],
        inputs["coeffs"],
        intercept=float(inputs.get("intercept", 0.0)),
        n_trajectories=int(inputs.get("n_trajectories", 10)),
        n_levels=int(inputs.get("n_levels", 4)),
        seed=inputs.get("seed"),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_dim": out["n_dim"],
            "converged": None,
            "backend": out["backend"],
        },
    }
