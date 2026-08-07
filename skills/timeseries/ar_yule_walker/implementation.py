"""timeseries.ar_yule_walker entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.timeseries.ar.ar_yule_walker`` — no estimator logic lives here.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.ar import ar_yule_walker


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = ar_yule_walker(
        inputs["series"],
        order=inputs["order"],
        demean=inputs.get("demean", True),
    )
    return {
        "result": out,
        "diagnostics": {
            "order_requested": out["order_requested"],
            "order_reached": out["order_reached"],
            "is_positive_definite": out["is_positive_definite"],
            "innovation_variance": out["innovation_variance"],
            "backend": out["backend"],
        },
    }
