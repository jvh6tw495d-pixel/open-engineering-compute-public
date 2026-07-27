"""Energy Specialist v0.1 — generic energy skills only (no private dispatch)."""

from __future__ import annotations

from agents.common import SkillSpecialist


class EnergySpecialist(SkillSpecialist):
    """Maps energy demos → energy/battery/timeseries public skills."""

    name = "energy_specialist"
    demos = {
        "balance": (
            "energy.balance",
            {
                "energy_in": [
                    {"value": 10.0, "unit": "Wh"},
                    {"value": 5.0, "unit": "Wh"},
                ],
                "energy_out": [{"value": 12.0, "unit": "Wh"}],
                "storage_delta": {"value": 3.0, "unit": "Wh"},
            },
        ),
        "load_metrics": (
            "energy.load_metrics",
            {
                "power_values": [
                    {"value": 10.0, "unit": "W"},
                    {"value": 20.0, "unit": "W"},
                    {"value": 15.0, "unit": "W"},
                    {"value": 5.0, "unit": "W"},
                ]
            },
        ),
        "soc_step": (
            "battery.soc_step",
            {
                "soc": 0.5,
                "power": {"value": 10.0, "unit": "W"},
                "dt_hours": {"value": 1.0, "unit": "h"},
                "capacity": {"value": 100.0, "unit": "Wh"},
            },
        ),
        "power_to_energy": (
            "timeseries.power_to_energy",
            {
                "timestamps": [
                    "2024-01-01T00:00:00",
                    "2024-01-01T01:00:00",
                ],
                "power": [1.0, 1.0],
                "power_unit": "kW",
                "energy_unit": "kWh",
            },
        ),
        "three_phase": (
            "electrical.three_phase_power",
            {
                "voltage_line_to_line": {"value": 400.0, "unit": "V"},
                "current_line": {"value": 100.0, "unit": "A"},
                "power_factor": 0.9,
                "power_factor_type": "lagging",
            },
        ),
    }
