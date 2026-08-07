"""End-to-end: electrical.three_phase_power through the real, sandboxed
ExecutionService -- registry -> validators -> dimensional normalization
(ADR 0016) -> subprocess -> status -> provenance. Mirrors
``test_optimize_scalar_end_to_end.py``; the first electrical skill, so
also the first end-to-end proof that ADR 0016's central normalization
actually reaches a real skill's implementation, not just the fixture
skills in ``tests/unit/test_execution_service.py``.
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
    skill = registry.get_skill("electrical.three_phase_power")
    input_validators, result_validators = build_validators(skill)
    return ExecutionService(
        registry, input_validators=input_validators, result_validators=result_validators
    )


def test_three_phase_power_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.three_phase_power",
            inputs={
                "voltage_line_to_line": {"value": 380.0, "unit": "V"},
                "current_line": {"value": 10.0, "unit": "A"},
                "power_factor": 0.8,
                "power_factor_type": "lagging",
            },
        )
    )

    # method.iterative: false, no converged concept, no errors/warnings -> VERIFIED
    assert result.status is ExecutionStatus.VERIFIED
    assert math.isclose(result.result["apparent_power"]["value"], 6581.793068761733, rel_tol=1e-9)
    assert math.isclose(result.result["active_power"]["value"], 5265.434455009387, rel_tol=1e-9)


def test_three_phase_power_normalizes_non_canonical_units() -> None:
    """ADR 0016: 0.38 kV must produce exactly the same result as 380 V --
    the skill's implementation never sees "kV", only the normalized "V"
    ExecutionService converted it to before the sandbox ran."""
    service = _service()
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
    non_canonical = service.execute(
        ExecutionRequest(
            skill_id="electrical.three_phase_power",
            inputs={
                "voltage_line_to_line": {"value": 0.38, "unit": "kV"},
                "current_line": {"value": 10000.0, "unit": "mA"},
                "power_factor": 0.8,
            },
        )
    )

    assert non_canonical.status is ExecutionStatus.VERIFIED
    assert non_canonical.result == canonical.result
    assert non_canonical.normalized_inputs["voltage_line_to_line"] == {"value": 380.0, "unit": "V"}
    assert non_canonical.normalized_inputs["current_line"] == {"value": 10.0, "unit": "A"}
    assert non_canonical.inputs["voltage_line_to_line"] == {"value": 0.38, "unit": "kV"}


def test_three_phase_power_incompatible_unit_is_invalid_without_executing() -> None:
    service = _service()
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


def test_three_phase_power_negative_voltage_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.three_phase_power",
            inputs={
                "voltage_line_to_line": {"value": -380.0, "unit": "V"},
                "current_line": {"value": 10.0, "unit": "A"},
                "power_factor": 0.8,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_three_phase_power_out_of_range_power_factor_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="electrical.three_phase_power",
            inputs={
                "voltage_line_to_line": {"value": 380.0, "unit": "V"},
                "current_line": {"value": 10.0, "unit": "A"},
                "power_factor": 1.5,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID
