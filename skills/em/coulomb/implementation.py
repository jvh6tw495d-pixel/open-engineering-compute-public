from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.electromagnetism import coulomb_force


def _qv(field: dict[str, Any]) -> QuantityValue:
    return QuantityValue(value=float(field["value"]), unit=field["unit"])


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    f = coulomb_force(_qv(inputs["charge1"]), _qv(inputs["charge2"]), _qv(inputs["separation"]))
    return {"result": {"force": f.model_dump(mode="json")}, "diagnostics": {}}
