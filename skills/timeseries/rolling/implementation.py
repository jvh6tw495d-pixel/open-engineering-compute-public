from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.quality import rolling_window


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = rolling_window(
        inputs["timestamps"],
        inputs["values"],
        window=int(inputs["window"]),
        how=inputs.get("how", "mean"),
        timezone=inputs.get("timezone"),
    )
    return {"result": out, "diagnostics": {"window": out["window"], "how": out["how"]}}
