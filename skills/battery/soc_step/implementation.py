from __future__ import annotations

from typing import Any

from oec.kernel.energy.metrics import soc_update
from oec.kernel.units.quantity import QuantityValue


def _value(raw: dict[str, Any], unit: str) -> float:
    return QuantityValue(**raw).convert_to(unit).value


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = soc_update(
        float(inputs["soc"]),
        _value(inputs["power"], "W"),
        _value(inputs["dt_hours"], "h"),
        _value(inputs["capacity"], "Wh"),
        efficiency_charge=float(inputs.get("efficiency_charge", 1.0)),
        efficiency_discharge=float(inputs.get("efficiency_discharge", 1.0)),
    )
    out["energy_delta"] = {"value": out["energy_delta"], "unit": "Wh"}
    return {"result": out, "diagnostics": {}}
