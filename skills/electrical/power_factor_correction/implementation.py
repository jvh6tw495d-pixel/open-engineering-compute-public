"""electrical.power_factor_correction entrypoint.

Closed-form capacitor-bank sizing for displacement power-factor
correction of a lagging load. Units already canonical (ADR 0016).
"""

from __future__ import annotations

import math
from typing import Any

_TWO_PI = 2.0 * math.pi


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    active_power = float(inputs["active_power"]["value"])
    existing_pf = float(inputs["existing_power_factor"])
    desired_pf = float(inputs["desired_power_factor"])
    voltage = float(inputs["voltage"]["value"])
    frequency = float(inputs["frequency"]["value"])
    phase_count: int = inputs["phase_count"]
    connection: str = inputs["connection"]

    existing_q = active_power * math.tan(math.acos(existing_pf))
    desired_q = active_power * math.tan(math.acos(desired_pf))
    capacitor_q = existing_q - desired_q

    omega = _TWO_PI * frequency
    capacitance_farad = _capacitance_farad(capacitor_q, omega, voltage, connection)
    capacitance_uf = capacitance_farad * 1.0e6

    return {
        "result": {
            "existing_reactive_power": {"value": existing_q, "unit": "var"},
            "desired_reactive_power": {"value": desired_q, "unit": "var"},
            "capacitor_reactive_power": {"value": capacitor_q, "unit": "var"},
            "capacitance_per_unit": {"value": capacitance_uf, "unit": "uF"},
            "connection": connection,
            "phase_count": phase_count,
        },
        "diagnostics": {},
    }


def _capacitance_farad(capacitor_q: float, omega: float, voltage: float, connection: str) -> float:
    """Return capacitance of each unit (F).

    Single-phase: Q = ω C V² → C = Q / (ω V²).
    Three-phase delta (each unit sees V_LL): Q_total = 3 ω C V_LL² → C = Q/(3 ω V²).
    Three-phase star (each unit sees V_LL/√3): Q_total = ω C V_LL² → C = Q/(ω V²).
    """
    if connection == "delta":
        return capacitor_q / (3.0 * omega * voltage * voltage)
    # single_phase and star share C = Q / (ω V²) with V = system voltage
    # (line for single-phase, line-to-line for star bank total identity).
    return capacitor_q / (omega * voltage * voltage)
