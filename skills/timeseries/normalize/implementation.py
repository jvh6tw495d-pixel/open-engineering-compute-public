from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.quality import normalize_series


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = normalize_series(
        inputs["timestamps"],
        inputs["values"],
        method=inputs.get("method", "minmax"),
        timezone=inputs.get("timezone"),
    )
    return {"result": out, "diagnostics": {"method": out["method"]}}
