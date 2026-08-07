"""timeseries.levinson_durbin entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.timeseries.ar.levinson_durbin`` — no recursion logic lives here.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.ar import levinson_durbin


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = levinson_durbin(inputs["autocorrelation"])
    return {
        "result": out,
        "diagnostics": {
            "order_requested": out["order_requested"],
            "order_reached": out["order_reached"],
            "is_positive_definite": out["is_positive_definite"],
            "backend": out["backend"],
        },
    }
