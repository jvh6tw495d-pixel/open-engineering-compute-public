from __future__ import annotations

from typing import Any

from oec.kernel.energy.metrics import energy_balance
from oec.kernel.units.quantity import QuantityValue

_ENERGY_UNIT = "Wh"


def _energy_value(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_ENERGY_UNIT).value


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = energy_balance(
        [_energy_value(value) for value in inputs.get("energy_in", [])],
        [_energy_value(value) for value in inputs.get("energy_out", [])],
        storage_delta=_energy_value(inputs.get("storage_delta", {"value": 0.0, "unit": "Wh"})),
        tolerance=_energy_value(inputs.get("tolerance", {"value": 1e-6, "unit": "Wh"})),
    )
    for field in ("total_in", "total_out", "storage_delta", "residual", "tolerance"):
        out[field] = {"value": out[field], "unit": _ENERGY_UNIT}
    return {"result": out, "diagnostics": {}}
