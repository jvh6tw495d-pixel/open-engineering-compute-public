"""uncertainty.lhs entrypoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.uncertainty.sampling import latin_hypercube


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = latin_hypercube(
        int(inputs["n_samples"]),
        inputs["bounds"],
        seed=inputs.get("seed"),
    )
    return {
        "result": out,
        "diagnostics": {
            "n_samples": out["n_samples"],
            "n_dim": out["n_dim"],
            "converged": None,
            "backend": out["backend"],
        },
    }
