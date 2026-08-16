"""timeseries.forecast_simple entrypoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.forecast import forecast_simple


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"steps_ahead": inputs["steps_ahead"], "method": inputs["method"]}
    if "period" in inputs:
        kwargs["period"] = inputs["period"]
    out = forecast_simple(inputs["series"], **kwargs)
    return {
        "result": out,
        "diagnostics": {
            "method": out["method"],
            "steps_ahead": out["steps_ahead"],
            "n_series": out["n_series"],
            "converged": out["converged"],
            "backend": out["backend"],
        },
    }
