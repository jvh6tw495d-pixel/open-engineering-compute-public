from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.ops import align_series


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = align_series(
        inputs["timestamps_a"],
        inputs["values_a"],
        inputs["timestamps_b"],
        inputs["values_b"],
        how=inputs.get("how", "inner"),
        timezone=inputs.get("timezone"),
    )
    return {"result": out, "diagnostics": {}}
