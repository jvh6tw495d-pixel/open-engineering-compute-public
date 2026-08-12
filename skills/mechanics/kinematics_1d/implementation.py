from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.mechanics import (
    uniform_acceleration_position,
    uniform_acceleration_velocity,
)


def _qv(field: dict[str, Any]) -> QuantityValue:
    return QuantityValue(value=float(field["value"]), unit=field["unit"])


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    v0 = _qv(inputs["v0"])
    a = _qv(inputs["a"])
    t = _qv(inputs["t"])
    x0 = _qv(inputs["x0"]) if "x0" in inputs else QuantityValue(value=0.0, unit="m")
    v = uniform_acceleration_velocity(v0, a, t)
    x = uniform_acceleration_position(x0, v0, a, t)
    return {
        "result": {
            "velocity": v.model_dump(mode="json"),
            "position": x.model_dump(mode="json"),
        },
        "diagnostics": {},
    }
