"""energy.service_metrics entrypoint.

Thin adapter over ``oec.physics.service_metrics`` (energy_delivered +
autonomy_hours). No commercial scoring.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.service_metrics import autonomy_hours, energy_delivered

_POWER_UNIT = "W"
_TIME_UNIT = "h"
_ENERGY_UNIT = "Wh"


def _power(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_POWER_UNIT).value


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    load = [_power(v) for v in inputs["load"]]
    pv = [_power(v) for v in inputs["pv"]]
    discharge = [_power(v) for v in inputs["storage_discharge"]]
    grid = [_power(v) for v in inputs["grid_import"]]
    dt = QuantityValue(**inputs["dt_hours"]).convert_to(_TIME_UNIT).value
    capacity = QuantityValue(**inputs["capacity"]).convert_to(_ENERGY_UNIT).value
    initial_soc = float(inputs["initial_soc"])

    e_del = energy_delivered(load, pv, discharge, grid, dt)
    hours = autonomy_hours(load, pv, capacity, initial_soc, dt)

    return {
        "result": {
            "energy_delivered": {"value": float(e_del), "unit": _ENERGY_UNIT},
            "autonomy_hours": {"value": float(hours), "unit": _TIME_UNIT},
        },
        "diagnostics": {},
    }
