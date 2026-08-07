"""electrical.per_unit_conversion entrypoint.

Classical per-unit bases and conversions. Units already canonical
(ADR 0016) for voltage_base / power_base / new_* bases. The free-form
``value`` quantity for ``to_per_unit`` cannot carry a single static
``x-oec-unit`` (the unit depends on ``quantity_kind``), so this module
normalizes it to ohm/V/A/W after ``validation.py`` has confirmed
convertibility.
"""

from __future__ import annotations

import math
from typing import Any

from oec.kernel.units.normalize import normalize
from oec.kernel.units.quantity import QuantityValue

_SQRT_3 = math.sqrt(3.0)

_ACTUAL_UNITS = {
    "impedance": "ohm",
    "voltage": "V",
    "current": "A",
    "power": "W",
}


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    operation: str = inputs["operation"]
    phase_count: int = inputs["phase_count"]
    v_base = float(inputs["voltage_base"]["value"])
    s_base = float(inputs["power_base"]["value"])

    z_base, i_base = _bases(v_base, s_base, phase_count)

    result: dict[str, Any] = {
        "impedance_base": {"value": z_base, "unit": "ohm"},
        "current_base": {"value": i_base, "unit": "A"},
        "new_impedance_base": None,
        "new_current_base": None,
        "operation": operation,
        "quantity_kind": inputs.get("quantity_kind"),
        "phase_count": phase_count,
    }

    if operation == "to_per_unit":
        kind: str = inputs["quantity_kind"]
        actual = _canonical_value(inputs["value"], kind)
        result["value_pu"] = _to_pu(actual, kind, v_base, s_base, z_base, i_base)
    elif operation == "from_per_unit":
        kind = inputs["quantity_kind"]
        value_pu = float(inputs["value_pu"])
        actual = _from_pu(value_pu, kind, v_base, s_base, z_base, i_base)
        result["value_actual"] = {"value": actual, "unit": _ACTUAL_UNITS[kind]}
        result["value_pu"] = value_pu
    else:  # change_base — impedance-style base change of a pu value
        old_pu = float(inputs["value_pu"])
        new_v = float(inputs["new_voltage_base"]["value"])
        new_s = float(inputs["new_power_base"]["value"])
        # Z_pu_new = Z_pu_old * (S_new/S_old) * (V_old/V_new)^2
        new_pu = old_pu * (new_s / s_base) * (v_base / new_v) ** 2
        new_z_base, new_i_base = _bases(new_v, new_s, phase_count)
        result["value_pu"] = new_pu
        result["quantity_kind"] = "impedance"
        # The OLD base's Z_base/current_base are already in the result
        # above (computed from voltage_base/power_base); a caller auditing
        # a base change needs the NEW base's derived quantities too, not
        # just the old ones -- reporting only the old pair was the actual
        # gap (Opus review, Sprint 08 Fase B).
        result["new_impedance_base"] = {"value": new_z_base, "unit": "ohm"}
        result["new_current_base"] = {"value": new_i_base, "unit": "A"}

    return {"result": result, "diagnostics": {}}


def _canonical_value(raw: dict[str, Any], kind: str) -> float:
    quantity = QuantityValue(value=float(raw["value"]), unit=str(raw["unit"]))
    return float(normalize(quantity, to_unit=_ACTUAL_UNITS[kind]).normalized.value)


def _bases(v_base: float, s_base: float, phase_count: int) -> tuple[float, float]:
    if phase_count == 1:
        i_base = s_base / v_base
        z_base = v_base / i_base  # == V^2 / S
    else:
        i_base = s_base / (_SQRT_3 * v_base)
        z_base = v_base / (_SQRT_3 * i_base)  # == V_LL^2 / S
    return z_base, i_base


def _to_pu(
    actual: float,
    kind: str,
    v_base: float,
    s_base: float,
    z_base: float,
    i_base: float,
) -> float:
    if kind == "impedance":
        return actual / z_base
    if kind == "voltage":
        return actual / v_base
    if kind == "current":
        return actual / i_base
    return actual / s_base  # power


def _from_pu(
    value_pu: float,
    kind: str,
    v_base: float,
    s_base: float,
    z_base: float,
    i_base: float,
) -> float:
    if kind == "impedance":
        return value_pu * z_base
    if kind == "voltage":
        return value_pu * v_base
    if kind == "current":
        return value_pu * i_base
    return value_pu * s_base
