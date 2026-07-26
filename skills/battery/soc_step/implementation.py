from __future__ import annotations

from typing import Any

from oec.kernel.energy.metrics import soc_update


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = soc_update(
        float(inputs["soc"]),
        float(inputs["power"]),
        float(inputs["dt_hours"]),
        float(inputs["capacity"]),
        efficiency_charge=float(inputs.get("efficiency_charge", 1.0)),
        efficiency_discharge=float(inputs.get("efficiency_discharge", 1.0)),
    )
    return {"result": out, "diagnostics": {}}
