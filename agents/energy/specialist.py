"""Energy Specialist v0.2 — public energy skills (no private dispatch)."""

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
        # Wave 4 / P1: canonical meshed DC linear power flow (D4).
        "dc_power_flow": (
            "electrical.dc_power_flow",
            {
                "lines": [
                    {"from_bus": "A", "to_bus": "B", "susceptance": 10.0},
                    {"from_bus": "B", "to_bus": "C", "susceptance": 10.0},
                    {"from_bus": "A", "to_bus": "C", "susceptance": 10.0},
                ],
                "injections": {"A": -1.0, "B": 0.4, "C": 0.6},
                "slack_bus": "A",
            },
        ),
        # v2.6.1 Wave 2 — energy-rich skills
        "hybrid_balance": (
            "energy.hybrid_balance",
            {
                "load": [
                    {"value": 3.0, "unit": "W"},
                    {"value": 2.0, "unit": "W"},
                ],
                "pv": [
                    {"value": 0.0, "unit": "W"},
                    {"value": 3.0, "unit": "W"},
                ],
                "grid_import": [
                    {"value": 3.0, "unit": "W"},
                    {"value": -0.5, "unit": "W"},
                ],
                "storage_charge": [
                    {"value": 0.0, "unit": "W"},
                    {"value": 0.5, "unit": "W"},
                ],
                "storage_discharge": [
                    {"value": 0.0, "unit": "W"},
                    {"value": 0.0, "unit": "W"},
                ],
                "dt_hours": {"value": 1.0, "unit": "h"},
            },
        ),
        "grid_zero_feasibility": (
            "energy.grid_zero_feasibility",
            {
                "load": [
                    {"value": 2.0, "unit": "W"},
                    {"value": 1.0, "unit": "W"},
                ],
                "pv": [
                    {"value": 0.5, "unit": "W"},
                    {"value": 1.5, "unit": "W"},
                ],
                "storage_charge": [
                    {"value": 0.0, "unit": "W"},
                    {"value": 0.5, "unit": "W"},
                ],
                "storage_discharge": [
                    {"value": 1.5, "unit": "W"},
                    {"value": 0.0, "unit": "W"},
                ],
                "grid_import": [
                    {"value": 0.0, "unit": "W"},
                    {"value": 0.0, "unit": "W"},
                ],
                "dt_hours": {"value": 1.0, "unit": "h"},
            },
        ),
        "pv_power": (
            "energy.pv_power",
            {
                "irradiance": {"value": 1000.0, "unit": "W / m ** 2"},
                "area": {"value": 10.0, "unit": "m ** 2"},
                "efficiency": 0.2,
            },
        ),
        "min_storage_capacity": (
            "energy.min_storage_capacity",
            {
                "load": [
                    {"value": 2.0, "unit": "Wh"},
                    {"value": 1.0, "unit": "Wh"},
                ],
                "pv": [
                    {"value": 0.0, "unit": "Wh"},
                    {"value": 0.0, "unit": "Wh"},
                ],
                "eta_charge": 1.0,
                "eta_discharge": 1.0,
                "soc_min": 0.0,
                "soc_max": 1.0,
                "initial_soc": 1.0,
                "horizon_hours": {"value": 2.0, "unit": "h"},
                "curtailment_allowed": False,
            },
        ),
        "soc_trajectory": (
            "battery.soc_trajectory",
            {
                "initial_soc": 0.5,
                "powers": [
                    {"value": 10.0, "unit": "W"},
                    {"value": -20.0, "unit": "W"},
                ],
                "dt_hours": {"value": 1.0, "unit": "h"},
                "capacity": {"value": 100.0, "unit": "Wh"},
                "eta_charge": 1.0,
                "eta_discharge": 1.0,
            },
        ),
        "service_metrics": (
            "energy.service_metrics",
            {
                "load": [
                    {"value": 10.0, "unit": "W"},
                    {"value": 20.0, "unit": "W"},
                ],
                "pv": [
                    {"value": 0.0, "unit": "W"},
                    {"value": 0.0, "unit": "W"},
                ],
                "storage_discharge": [
                    {"value": 10.0, "unit": "W"},
                    {"value": 20.0, "unit": "W"},
                ],
                "grid_import": [
                    {"value": 0.0, "unit": "W"},
                    {"value": 0.0, "unit": "W"},
                ],
                "dt_hours": {"value": 1.0, "unit": "h"},
                "capacity": {"value": 50.0, "unit": "Wh"},
                "initial_soc": 1.0,
            },
        ),
    }
