"""timeseries.backtest entrypoint."""

from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.backtest import backtest


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"steps_ahead": inputs["steps_ahead"], "method": inputs["method"]}
    if "period" in inputs:
        kwargs["period"] = inputs["period"]
    if "n_evaluations" in inputs:
        kwargs["n_evaluations"] = inputs["n_evaluations"]
    out = backtest(inputs["series"], **kwargs)
    return {
        "result": out,
        "diagnostics": {
            "method": out["method"],
            "n_evaluations": out["n_evaluations"],
            "mae": out["mae"],
            "rmse": out["rmse"],
            "converged": out["converged"],
            "backend": out["backend"],
        },
    }
