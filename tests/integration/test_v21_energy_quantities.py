from __future__ import annotations

from oec import sdk
from oec.execution.models import ExecutionStatus


def test_energy_balance_quantity_contract_end_to_end() -> None:
    result = sdk.Engine(skills_root="skills").run(
        "energy.balance",
        {
            "energy_in": [{"value": 1.0, "unit": "kWh"}],
            "energy_out": [{"value": 750.0, "unit": "Wh"}],
            "storage_delta": {"value": 250.0, "unit": "Wh"},
        },
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert result.result["total_in"] == {"value": 1000.0, "unit": "Wh"}
    assert result.result["balanced"] is True


def test_load_metrics_quantity_contract_end_to_end() -> None:
    result = sdk.Engine(skills_root="skills").run(
        "energy.load_metrics",
        {"power_values": [{"value": 1.0, "unit": "kW"}, {"value": 500.0, "unit": "W"}]},
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert result.result["average"] == {"value": 750.0, "unit": "W"}
    assert result.result["load_factor"] == 0.75


def test_soc_step_quantity_contract_end_to_end() -> None:
    result = sdk.Engine(skills_root="skills").run(
        "battery.soc_step",
        {
            "soc": 0.5,
            "power": {"value": 0.01, "unit": "kW"},
            "dt_hours": {"value": 60.0, "unit": "min"},
            "capacity": {"value": 0.1, "unit": "kWh"},
        },
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert result.result["soc"] == 0.6
    assert result.result["energy_delta"] == {"value": 10.0, "unit": "Wh"}
