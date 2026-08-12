from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.electromagnetism import (
    capacitor_energy,
    parallel_plate_capacitance,
    parallel_plate_field,
)


def _qv(field: dict[str, Any]) -> QuantityValue:
    return QuantityValue(value=float(field["value"]), unit=field["unit"])


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    c = parallel_plate_capacitance(
        _qv(inputs["area"]),
        _qv(inputs["gap"]),
        relative_permittivity=float(inputs.get("relative_permittivity", 1.0)),
    )
    result: dict[str, Any] = {"capacitance": c.model_dump(mode="json")}
    if "voltage" in inputs:
        v = _qv(inputs["voltage"])
        result["electric_field"] = parallel_plate_field(v, _qv(inputs["gap"])).model_dump(
            mode="json"
        )
        result["energy"] = capacitor_energy(c, v).model_dump(mode="json")
    return {"result": result, "diagnostics": {}}
