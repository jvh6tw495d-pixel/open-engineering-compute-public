"""End-to-end: electrical.per_unit_conversion through ExecutionService."""

import math
from pathlib import Path

from oec.execution.factory import build_validators
from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry

_SKILLS_ROOT = Path("skills")


def _service() -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS_ROOT)
    assert not report.failures, f"skill(s) failed to load: {report.failures}"
    skill = registry.get_skill("electrical.per_unit_conversion")
    input_validators, result_validators = build_validators(skill)
    return ExecutionService(
        registry, input_validators=input_validators, result_validators=result_validators
    )


def test_per_unit_conversion_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.per_unit_conversion",
            inputs={
                "operation": "to_per_unit",
                "quantity_kind": "impedance",
                "phase_count": 3,
                "voltage_base": {"value": 13.8, "unit": "kV"},
                "power_base": {"value": 100.0, "unit": "MVA"},
                "value": {"value": 0.5, "unit": "ohm"},
            },
        )
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert math.isclose(result.result["value_pu"], 0.26254988447805083, rel_tol=1e-9)


def test_per_unit_change_base_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.per_unit_conversion",
            inputs={
                "operation": "change_base",
                "phase_count": 3,
                "voltage_base": {"value": 13800.0, "unit": "V"},
                "power_base": {"value": 100.0, "unit": "MVA"},
                "value_pu": 0.1,
                "new_voltage_base": {"value": 13800.0, "unit": "V"},
                "new_power_base": {"value": 50.0, "unit": "MVA"},
            },
        )
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert math.isclose(result.result["value_pu"], 0.05, rel_tol=1e-12)


def test_per_unit_wrong_value_unit_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.per_unit_conversion",
            inputs={
                "operation": "to_per_unit",
                "quantity_kind": "impedance",
                "phase_count": 3,
                "voltage_base": {"value": 13800.0, "unit": "V"},
                "power_base": {"value": 100_000_000.0, "unit": "W"},
                "value": {"value": 0.5, "unit": "V"},
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID
