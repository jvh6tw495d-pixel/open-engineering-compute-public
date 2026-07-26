from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.timegrid import build_timegrid


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = build_timegrid(
        inputs["start"],
        inputs["end"],
        freq=inputs["freq"],
        timezone=inputs.get("timezone"),
    )
    return {"result": out, "diagnostics": {"n_points": out["n_points"]}}
