from __future__ import annotations

from typing import Any

from oec.kernel.units.quantity import QuantityValue
from oec.physics.conservation import ConservationError, evaluate_residual

_ENERGY_UNIT = "Wh"


def _energy_value(raw: dict[str, Any]) -> float:
    return QuantityValue(**raw).convert_to(_ENERGY_UNIT).value


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    energy_in = [_energy_value(value) for value in inputs.get("energy_in", [])]
    energy_out = [_energy_value(value) for value in inputs.get("energy_out", [])]
    if not energy_in and not energy_out:
        raise ConservationError(
            "energy_in and energy_out cannot both be empty",
            details={},
        )
    storage_delta = _energy_value(inputs.get("storage_delta", {"value": 0.0, "unit": _ENERGY_UNIT}))
    tolerance = _energy_value(inputs.get("tolerance", {"value": 1e-6, "unit": _ENERGY_UNIT}))
    total_in = float(sum(energy_in))
    total_out = float(sum(energy_out))
    residual = total_in - total_out - float(storage_delta)
    check = evaluate_residual(
        residual,
        atol=float(tolerance),
        rtol=0.0,
        scale=1.0,
        unit=_ENERGY_UNIT,
    )
    out = {
        "total_in": total_in,
        "total_out": total_out,
        "storage_delta": float(storage_delta),
        "residual": residual,
        "balanced": check.balanced,
        "tolerance": float(tolerance),
    }
    for field in ("total_in", "total_out", "storage_delta", "residual", "tolerance"):
        out[field] = {"value": out[field], "unit": _ENERGY_UNIT}
    return {"result": out, "diagnostics": {}}
