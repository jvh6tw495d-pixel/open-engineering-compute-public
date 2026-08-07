"""energy.pv_power entrypoint.

Thin adapter over ``oec.physics.pv.pv_power``. No inline PV arithmetic.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.pv import pv_power

_IRRADIANCE_UNIT = "W / m ** 2"
_AREA_UNIT = "m ** 2"
_TEMP_UNIT = "degC"
_POWER_UNIT = "W"


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    irradiance = QuantityValue(**inputs["irradiance"]).convert_to(_IRRADIANCE_UNIT).value
    area = QuantityValue(**inputs["area"]).convert_to(_AREA_UNIT).value
    efficiency = float(inputs["efficiency"])

    kwargs: dict[str, Any] = {}
    if "temperature" in inputs or "temperature_coefficient" in inputs:
        if "temperature" not in inputs or "temperature_coefficient" not in inputs:
            raise ValueError(
                "temperature and temperature_coefficient must both be provided or both omitted"
            )
        kwargs["temperature"] = QuantityValue(**inputs["temperature"]).convert_to(_TEMP_UNIT).value
        kwargs["temperature_coefficient"] = float(inputs["temperature_coefficient"])
    if "reference_temperature" in inputs:
        kwargs["reference_temperature"] = (
            QuantityValue(**inputs["reference_temperature"]).convert_to(_TEMP_UNIT).value
        )

    out = pv_power(irradiance, area, efficiency, **kwargs)
    return {
        "result": {
            "power": {"value": float(out["power"]), "unit": _POWER_UNIT},
            "temperature_factor": float(out["temperature_factor"]),
            "efficiency_effective": float(out["efficiency_effective"]),
        },
        "diagnostics": {},
    }
