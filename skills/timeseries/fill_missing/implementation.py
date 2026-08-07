from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.ops import fill_missing


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = fill_missing(
        inputs["timestamps"],
        inputs["values"],
        method=inputs.get("method", "ffill"),
        timezone=inputs.get("timezone"),
    )
    return {"result": out, "diagnostics": {}}
