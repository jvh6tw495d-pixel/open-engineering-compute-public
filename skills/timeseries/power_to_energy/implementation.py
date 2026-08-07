from __future__ import annotations

from typing import Any

from oec.kernel.timeseries.ops import power_to_energy


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = power_to_energy(
        inputs["timestamps"],
        inputs["power"],
        power_unit=inputs.get("power_unit", "kW"),
        energy_unit=inputs.get("energy_unit", "kWh"),
        timezone=inputs.get("timezone"),
    )
    return {"result": out, "diagnostics": {}}
