from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.statistical import ideal_gas_pressure, rms_speed_monatomic


def _qv(field: dict[str, Any]) -> QuantityValue:
    return QuantityValue(value=float(field["value"]), unit=field["unit"])


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    p = ideal_gas_pressure(
        float(inputs["amount_mol"]),
        _qv(inputs["temperature"]),
        _qv(inputs["volume"]),
    )
    result: dict[str, Any] = {"pressure": p.model_dump(mode="json")}
    if "molar_mass_kg_per_mol" in inputs:
        result["rms_speed"] = rms_speed_monatomic(
            float(inputs["molar_mass_kg_per_mol"]), _qv(inputs["temperature"])
        ).model_dump(mode="json")
    return {"result": result, "diagnostics": {}}
