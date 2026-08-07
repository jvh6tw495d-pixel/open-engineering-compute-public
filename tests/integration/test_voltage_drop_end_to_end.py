"""End-to-end: electrical.voltage_drop through the sandboxed ExecutionService."""

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
    skill = registry.get_skill("electrical.voltage_drop")
    input_validators, result_validators = build_validators(skill)
    return ExecutionService(
        registry, input_validators=input_validators, result_validators=result_validators
    )


def test_voltage_drop_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.voltage_drop",
            inputs={
                "load_type": "current",
                "phase_count": 1,
                "voltage_reference": {"value": 230.0, "unit": "V"},
                "power_factor": 0.8,
                "length": {"value": 50.0, "unit": "m"},
                "current": {"value": 10.0, "unit": "A"},
                "resistance_per_length": {"value": 0.001, "unit": "ohm/m"},
            },
        )
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert math.isclose(result.result["voltage_drop"]["value"], 0.8, rel_tol=1e-9)


def test_voltage_drop_normalizes_length_units() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.voltage_drop",
            inputs={
                "load_type": "current",
                "phase_count": 1,
                "voltage_reference": {"value": 230.0, "unit": "V"},
                "power_factor": 0.8,
                "length": {"value": 0.05, "unit": "km"},
                "current": {"value": 10.0, "unit": "A"},
                "resistance_per_length": {"value": 0.001, "unit": "ohm/m"},
            },
        )
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert math.isclose(result.result["voltage_drop"]["value"], 0.8, rel_tol=1e-9)
    assert result.normalized_inputs["length"] == {"value": 50.0, "unit": "m"}


def test_voltage_drop_missing_resistance_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.voltage_drop",
            inputs={
                "load_type": "current",
                "phase_count": 1,
                "voltage_reference": {"value": 230.0, "unit": "V"},
                "power_factor": 0.8,
                "length": {"value": 50.0, "unit": "m"},
                "current": {"value": 10.0, "unit": "A"},
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID
