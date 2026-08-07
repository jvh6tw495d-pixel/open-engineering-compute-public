"""Phase A2: units policy regressions (electrical + dimensional INVALID)."""

from pathlib import Path

from oec.execution.factory import build_validators
from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry

_SKILLS = Path("skills")


def _service(skill_id: str) -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS)
    assert not report.failures
    skill = registry.get_skill(skill_id)
    iv, rv = build_validators(skill)
    return ExecutionService(registry, input_validators=iv, result_validators=rv)


def test_three_phase_power_kv_ma_matches_canonical_si() -> None:
    service = _service("electrical.three_phase_power")
    canonical = service.execute(
        ExecutionRequest(
            skill_id="electrical.three_phase_power",
            inputs={
                "voltage_line_to_line": {"value": 380.0, "unit": "V"},
                "current_line": {"value": 10.0, "unit": "A"},
                "power_factor": 0.8,
            },
        )
    )
    alt = service.execute(
        ExecutionRequest(
            skill_id="electrical.three_phase_power",
            inputs={
                "voltage_line_to_line": {"value": 0.38, "unit": "kV"},
                "current_line": {"value": 10000.0, "unit": "mA"},
                "power_factor": 0.8,
            },
        )
    )
    assert canonical.status is ExecutionStatus.VERIFIED
    assert alt.status is ExecutionStatus.VERIFIED
    assert alt.result == canonical.result
    assert alt.normalized_inputs["voltage_line_to_line"]["unit"] == "V"
    assert alt.provenance.get("input_hash")
    assert alt.provenance.get("backends")


def test_incompatible_voltage_unit_is_invalid() -> None:
    service = _service("electrical.three_phase_power")
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.three_phase_power",
            inputs={
                "voltage_line_to_line": {"value": 380.0, "unit": "A"},
                "current_line": {"value": 10.0, "unit": "A"},
                "power_factor": 0.8,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID
    outcomes = result.validation["outcomes"]
    assert any(o["severity"] == "error" and o["layer"] == "dimensional" for o in outcomes)
