"""timeseries.autocorrelation entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.timeseries.ar.autocorrelation`` — no estimator logic lives here.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.ar import autocorrelation


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = autocorrelation(
        inputs["series"],
        nlags=inputs["nlags"],
        method=inputs.get("method", "biased"),
        demean=inputs.get("demean", True),
    )
    return {
        "result": out,
        "diagnostics": {
            "n": out["n"],
            "nlags": out["nlags"],
            "method": out["method"],
            "backend": out["backend"],
        },
    }
