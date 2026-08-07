"""energy.hybrid_balance entrypoint.

Thin adapter over ``oec.physics.hybrid.hybrid_balance``. Power series are
converted to energy via ``dt_hours`` (Wh = W · h). No inline residual formula.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.hybrid import hybrid_balance

_POWER_UNIT = "W"
_TIME_UNIT = "h"
_ENERGY_UNIT = "Wh"


def _power(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_POWER_UNIT).value


def _hours(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_TIME_UNIT).value


def _check_dump(check: Any) -> dict[str, Any]:
    if hasattr(check, "model_dump"):
        return check.model_dump(mode="json")
    return dict(check)


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

    out = hybrid_balance(**kwargs)
    period_checks = {key: _check_dump(val) for key, val in out["period_checks"].items()}
    aggregate = _check_dump(out["balance"])

    return {
        "result": {
            "n": int(out["n"]),
            "residuals": list(out["residuals"]),
            "supply": list(out["supply"]),
            "period_checks": period_checks,
            "aggregate": aggregate,
            "balanced": bool(out["balanced"]),
            "unit": _ENERGY_UNIT,
            "atol": float(out["atol"]),
            "rtol": float(out["rtol"]),
            "scale": float(out["scale"]),
        },
        "diagnostics": {},
    }
