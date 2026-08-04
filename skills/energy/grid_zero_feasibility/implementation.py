"""energy.grid_zero_feasibility entrypoint.

Thin adapter over ``oec.physics.grid_zero.grid_zero_feasibility``.
**No** solver / HiGHS — physics-only trajectory check.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.grid_zero import grid_zero_feasibility

_POWER_UNIT = "W"
_TIME_UNIT = "h"
_ENERGY_UNIT = "Wh"


def _power(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_POWER_UNIT).value


def _hours(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_TIME_UNIT).value


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    dt = _hours(inputs["dt_hours"])
    load = [_power(v) * dt for v in inputs["load"]]
    pv = [_power(v) * dt for v in inputs["pv"]]
    grid = [_power(v) * dt for v in inputs["grid_import"]]
    charge = [_power(v) * dt for v in inputs["storage_charge"]]
    discharge = [_power(v) * dt for v in inputs["storage_discharge"]]

    kwargs: dict[str, Any] = {
        "load": load,
        "pv": pv,
        "grid_import": grid,
        "charge": charge,
        "discharge": discharge,
        "unit": _ENERGY_UNIT,
    }
    if "atol" in inputs:
        kwargs["atol"] = float(inputs["atol"])
    if "rtol" in inputs:
        kwargs["rtol"] = float(inputs["rtol"])

    out = grid_zero_feasibility(**kwargs)
    flags = dict(out["flags"])
    # Keep flags JSON-serializable (lists of bool already are).
    return {
        "result": {
            "feasible": bool(out["feasible"]),
            "deficit_per_period": list(out["deficit_per_period"]),
            "balance_residual": list(out["balance_residual"]),
            "flags": flags,
            "n": int(out["n"]),
            "unit": _ENERGY_UNIT,
            "tolerance": float(out["tolerance"]),
        },
        "diagnostics": {},
    }
