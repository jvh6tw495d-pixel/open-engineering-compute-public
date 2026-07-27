from __future__ import annotations

from typing import Any

from oec.kernel.energy.metrics import load_metrics
from oec.kernel.units.quantity import QuantityValue

_POWER_UNIT = "W"


def _power_value(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_POWER_UNIT).value


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    out = load_metrics([_power_value(value) for value in inputs["power_values"]])
    for field in ("peak", "average", "min"):
        out[field] = {"value": out[field], "unit": _POWER_UNIT}
    return {"result": out, "diagnostics": {}}
