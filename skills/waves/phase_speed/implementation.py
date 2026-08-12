from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.waves import (
    angular_frequency,
    period_from_frequency,
    phase_speed,
    wave_number,
)


def _qv(field: dict[str, Any]) -> QuantityValue:
    return QuantityValue(value=float(field["value"]), unit=field["unit"])


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    f = _qv(inputs["frequency"])
    lam = _qv(inputs["wavelength"])
    v = phase_speed(f, lam)
    return {
        "result": {
            "phase_speed": v.model_dump(mode="json"),
            "period": period_from_frequency(f).model_dump(mode="json"),
            "angular_frequency": angular_frequency(f).model_dump(mode="json"),
            "wave_number": wave_number(lam).model_dump(mode="json"),
        },
        "diagnostics": {},
    }
