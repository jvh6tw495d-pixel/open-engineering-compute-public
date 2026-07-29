"""timeseries.pacf entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.timeseries.ar.pacf`` — no estimator logic lives here.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.ar import pacf


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = pacf(
        inputs["series"],
        nlags=inputs["nlags"],
        method=inputs.get("method", "levinson-durbin"),
        demean=inputs.get("demean", True),
    )
    return {
        "result": out,
        "diagnostics": {
            "n": out["n"],
            "nlags": out["nlags"],
            "order_reached": out["order_reached"],
            "is_positive_definite": out["is_positive_definite"],
            "backend": out["backend"],
        },
    }
