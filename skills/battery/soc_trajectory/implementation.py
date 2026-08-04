"""battery.soc_trajectory entrypoint.

Thin adapter over ``oec.physics.storage.storage_trajectory`` (energy-based).
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.storage import storage_trajectory

_POWER_UNIT = "W"
_TIME_UNIT = "h"
_ENERGY_UNIT = "Wh"


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    powers = [QuantityValue(**raw).convert_to(_POWER_UNIT).value for raw in inputs["powers"]]
    dt = QuantityValue(**inputs["dt_hours"]).convert_to(_TIME_UNIT).value
    capacity = QuantityValue(**inputs["capacity"]).convert_to(_ENERGY_UNIT).value
    out = storage_trajectory(
        float(inputs["initial_soc"]),
        powers,
        dt,
        capacity,
        efficiency_charge=float(inputs["eta_charge"]),
        efficiency_discharge=float(inputs["eta_discharge"]),
    )
    return {
        "result": {
            "soc_path": list(out["soc_path"]),
            "soc": list(out["soc"]),
            "delta_soc": list(out["delta_soc"]),
            "energy_delta": [float(e) for e in out["energy_delta"]],
            "unit": _ENERGY_UNIT,
            "clipped": list(out["clipped"]),
            "any_clipped": bool(out["any_clipped"]),
            "soc_final": float(out["soc_final"]),
        },
        "diagnostics": {},
    }
