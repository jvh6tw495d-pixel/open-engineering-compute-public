"""End-to-end: electrical.current_from_power through the real, sandboxed
ExecutionService. Mirrors ``test_three_phase_power_end_to_end.py``.
"""

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
    skill = registry.get_skill("electrical.current_from_power")
    input_validators, result_validators = build_validators(skill)
    return ExecutionService(
        registry, input_validators=input_validators, result_validators=result_validators
    )


def test_current_from_power_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.current_from_power",
            inputs={
                "power": {"value": 1000.0, "unit": "W"},
                "power_type": "active",
                "voltage": {"value": 230.0, "unit": "V"},
                "phase_count": 1,
                "power_factor": 0.8,
            },
        )
    )

    assert result.status is ExecutionStatus.VERIFIED
    assert math.isclose(result.result["current"]["value"], 5.434782608695652, rel_tol=1e-9)


def test_current_from_power_normalizes_non_canonical_units() -> None:
    """ADR 0016: 1 kW must produce the same result as 1000 W."""
    service = _service()
    canonical = service.execute(
        ExecutionRequest(
            skill_id="electrical.current_from_power",
            inputs={
                "power": {"value": 1000.0, "unit": "W"},
                "power_type": "active",
                "voltage": {"value": 230.0, "unit": "V"},
                "phase_count": 1,
                "power_factor": 0.8,
            },
        )
    )
    non_canonical = service.execute(
        ExecutionRequest(
            skill_id="electrical.current_from_power",
            inputs={
                "power": {"value": 1.0, "unit": "kW"},
                "power_type": "active",
                "voltage": {"value": 0.23, "unit": "kV"},
                "phase_count": 1,
                "power_factor": 0.8,
            },
        )
    )

    assert non_canonical.status is ExecutionStatus.VERIFIED
    assert non_canonical.result == canonical.result


def test_current_from_power_apparent_with_power_factor_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.current_from_power",
            inputs={
                "power": {"value": 1000.0, "unit": "VA"},
                "power_type": "apparent",
                "voltage": {"value": 230.0, "unit": "V"},
                "phase_count": 1,
                "power_factor": 0.8,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID
