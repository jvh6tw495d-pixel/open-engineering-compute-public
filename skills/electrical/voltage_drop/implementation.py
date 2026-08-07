"""electrical.voltage_drop entrypoint.

Runs inside the sandboxed subprocess (ADR 0012). Closed-form, not
iterative (``method.iterative: false``). By the time this runs,
``ExecutionService`` has already converted every ``x-oec-unit`` field to
its canonical unit (ADR 0016) — this module never does its own unit
conversion.

Resistivity constants (IEC 60228 annealed conductors at 20 °C, expressed
as Ω·mm²/m so that ``R = rho / A_mm2`` yields Ω/m directly):

- copper: 0.017241 Ω·mm²/m
- aluminum: 0.028264 Ω·mm²/m
"""

from __future__ import annotations

import math
from typing import Any

_SQRT_3 = math.sqrt(3.0)

# IEC 60228 approximate DC resistivities at 20 °C, Ω·mm²/m.
_RESISTIVITY_OHM_MM2_PER_M: dict[str, float] = {
    "copper": 0.017241,
    "aluminum": 0.028264,
}


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    load_type: str = inputs["load_type"]
    phase_count: int = inputs["phase_count"]
    voltage_ref = float(inputs["voltage_reference"]["value"])
    power_factor = float(inputs["power_factor"])
    power_factor_type: str = inputs.get("power_factor_type", "lagging")
    length = float(inputs["length"]["value"])

    resistance_per_length = _resolve_resistance_per_length(inputs)
    reactance_per_length = float(inputs.get("reactance_per_length", {"value": 0.0})["value"])

    current = _resolve_current(inputs, load_type, phase_count, voltage_ref, power_factor)

    sin_phi = math.sin(math.acos(power_factor))
    # Lagging (inductive): R cosφ + X sinφ. Leading (capacitive): R cosφ − X sinφ.
    # A negative result is a voltage *rise* — reported honestly, not abs()'d.
    rx_term = resistance_per_length * power_factor
    if power_factor_type == "lagging":
        rx_term += reactance_per_length * sin_phi
    else:
        rx_term -= reactance_per_length * sin_phi

    if phase_count == 1:
        # One-way length; the factor of 2 accounts for the out-and-back path.
        voltage_drop = 2.0 * current * length * rx_term
    else:
        # Line-to-line voltage drop for a balanced three-phase feeder.
        voltage_drop = _SQRT_3 * current * length * rx_term

    voltage_drop_percent = (voltage_drop / voltage_ref) * 100.0

    return {
        "result": {
            "voltage_drop": {"value": voltage_drop, "unit": "V"},
            "voltage_drop_percent": voltage_drop_percent,
            "current_used": {"value": current, "unit": "A"},
            "resistance_per_length_used": {
                "value": resistance_per_length,
                "unit": "ohm/m",
            },
            "reactance_per_length_used": {
                "value": reactance_per_length,
                "unit": "ohm/m",
            },
            "phase_count": phase_count,
            "power_factor_type": power_factor_type,
        },
        "diagnostics": {},
    }


def _resolve_resistance_per_length(inputs: dict[str, Any]) -> float:
    if "resistance_per_length" in inputs:
        return float(inputs["resistance_per_length"]["value"])
    material: str = inputs["material"]
    cross_section = float(inputs["cross_section"]["value"])
    return _RESISTIVITY_OHM_MM2_PER_M[material] / cross_section


def _resolve_current(
    inputs: dict[str, Any],
    load_type: str,
    phase_count: int,
    voltage_ref: float,
    power_factor: float,
) -> float:
    if load_type == "current":
        return float(inputs["current"]["value"])

    power = float(inputs["power"]["value"])
    if phase_count == 1:
        return power / (voltage_ref * power_factor)
    return power / (_SQRT_3 * voltage_ref * power_factor)
