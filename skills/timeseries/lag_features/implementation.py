"""timeseries.lag_features entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Wraps
``oec.kernel.timeseries.lag.lag_features``.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.lag import lag_features


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = lag_features(inputs["values"], inputs["lags"])
    return {
        "result": {
            "lags": out["lags"],
            "columns": out["columns"],
            "y": out["y"],
            "n_keep": out["n_keep"],
            "n_original": out["n_original"],
            "max_lag": out["max_lag"],
            "backend": "numpy",
            "converged": None,
        },
        "diagnostics": {
            "n_keep": out["n_keep"],
            "max_lag": out["max_lag"],
            "converged": None,
            "backend": "numpy",
        },
    }
