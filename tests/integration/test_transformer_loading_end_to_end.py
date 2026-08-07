"""End-to-end: electrical.transformer_loading through ExecutionService."""

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
    skill = registry.get_skill("electrical.transformer_loading")
    input_validators, result_validators = build_validators(skill)
    return ExecutionService(
        registry, input_validators=input_validators, result_validators=result_validators
    )


def test_transformer_loading_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.transformer_loading",
            inputs={
                "rated_apparent_power": {"value": 1000.0, "unit": "kVA"},
                "load_type": "apparent_power",
                "load_apparent_power": {"value": 800.0, "unit": "kVA"},
            },
        )
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert result.result["loading_percent"] == 80.0
    assert result.result["overload_warning"] is False
    assert result.normalized_inputs["rated_apparent_power"]["unit"] == "W"


def test_transformer_loading_overload_from_current() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.transformer_loading",
            inputs={
                "rated_apparent_power": {"value": 500.0, "unit": "kVA"},
                "load_type": "current",
                "load_current": {"value": 120.0, "unit": "A"},
                "rated_current": {"value": 100.0, "unit": "A"},
            },
        )
    )
    assert result.status is ExecutionStatus.VERIFIED
    assert result.result["loading_percent"] == 120.0
    assert result.result["overload_warning"] is True
