"""End-to-end: mathematics.solve_root through the real, sandboxed
ExecutionService -- the first real MVP skill (plan section 14.1)
exercised through the whole pipeline (registry -> validators -> subprocess
-> status -> provenance), not a loader/registry test fixture.

Validators are assembled via
``oec.execution.factory.build_validators`` (ADR 0014) from the skill's
own manifest -- this is also the regression guard that auto-discovery
reproduces exactly the hand-wired validator list this test used through
Sprint 05.
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
    skill = registry.get_skill("mathematics.solve_root")
    input_validators, result_validators = build_validators(skill)
    return ExecutionService(
        registry, input_validators=input_validators, result_validators=result_validators
    )


def test_solve_root_bracketed_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.solve_root",
            inputs={"expression": "x**2 - 2", "bracket": [0, 2]},
        )
    )

    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["root"], math.sqrt(2), rel_tol=1e-9)
    assert result.result["method"] == "brentq"
    assert result.diagnostics["converged"] is True


def test_solve_root_schema_violation_is_invalid_without_executing() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.solve_root",
            inputs={"expression": "x**2 - 2", "bracket": [0, 2], "unexpected_field": True},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_solve_root_bad_bracket_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.solve_root",
            inputs={"expression": "x**2 - 2", "bracket": [0, 1]},
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_solve_root_missing_locator_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(skill_id="mathematics.solve_root", inputs={"expression": "x**2 - 2"})
    )
    assert result.status is ExecutionStatus.INVALID
