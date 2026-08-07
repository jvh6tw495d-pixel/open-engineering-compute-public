from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.quality import clip_series


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = clip_series(
        inputs["timestamps"],
        inputs["values"],
        lower=inputs.get("lower"),
        upper=inputs.get("upper"),
        timezone=inputs.get("timezone"),
    )
    return {"result": out, "diagnostics": {"n_changed": out["n_changed"]}}
