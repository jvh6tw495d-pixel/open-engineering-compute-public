from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.quality import detect_outliers


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = detect_outliers(
        inputs["timestamps"],
        inputs["values"],
        method=inputs.get("method", "zscore"),
        threshold=float(inputs.get("threshold", 3.0)),
        timezone=inputs.get("timezone"),
    )
    return {"result": out, "diagnostics": {"n_outliers": out["n_outliers"]}}
