from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.ops import resample_series


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = resample_series(
        inputs["timestamps"],
        inputs["values"],
        freq=inputs["freq"],
        how=inputs.get("how", "mean"),
        timezone=inputs.get("timezone"),
    )
    return {"result": out, "diagnostics": {}}
