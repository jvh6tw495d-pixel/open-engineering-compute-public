"""End-to-end: electrical.power_factor_correction through ExecutionService."""

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
    skill = registry.get_skill("electrical.power_factor_correction")
    input_validators, result_validators = build_validators(skill)
    return ExecutionService(
        registry, input_validators=input_validators, result_validators=result_validators
    )


def test_power_factor_correction_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.power_factor_correction",
            inputs={
                "active_power": {"value": 100.0, "unit": "kW"},
                "existing_power_factor": 0.8,
                "desired_power_factor": 0.95,
                "voltage": {"value": 380.0, "unit": "V"},
                "frequency": {"value": 50.0, "unit": "Hz"},
                "phase_count": 3,
                "connection": "delta",
            },
        )
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert math.isclose(
        result.result["capacitor_reactive_power"]["value"],
        42131.58948211365,
        rel_tol=1e-9,
    )


def test_power_factor_correction_desired_below_existing_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.power_factor_correction",
            inputs={
                "active_power": {"value": 10000.0, "unit": "W"},
                "existing_power_factor": 0.95,
                "desired_power_factor": 0.8,
                "voltage": {"value": 230.0, "unit": "V"},
                "frequency": {"value": 50.0, "unit": "Hz"},
                "phase_count": 1,
                "connection": "single_phase",
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID
