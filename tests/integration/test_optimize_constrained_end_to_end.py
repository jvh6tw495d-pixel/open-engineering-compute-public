"""End-to-end: mathematics.optimize_constrained through the real,
sandboxed ExecutionService -- registry -> validators -> subprocess ->
status -> provenance. Mirrors ``test_optimize_scalar_end_to_end.py``.

Validators are assembled via ``oec.execution.factory.build_validators``
(ADR 0014) from the skill's own manifest -- this is also the regression
guard that auto-discovery reproduces exactly the hand-wired validator
list this test used through Sprint 05.
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
    skill = registry.get_skill("mathematics.optimize_constrained")
    input_validators, result_validators = build_validators(skill)
    return ExecutionService(
        registry, input_validators=input_validators, result_validators=result_validators
    )


def test_optimize_constrained_end_to_end() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_constrained",
            inputs={
                "variables": ["x", "y"],
                "expression": "x**2 + y**2",
                "x0": [0.0, 0.0],
                "bounds": [[-10, 10], [-10, 10]],
                "constraints": [{"type": "ineq", "expression": "x + y - 1"}],
            },
        )
    )

    # iterative:true + converged + no warnings -> VALIDATED
    assert result.status is ExecutionStatus.VALIDATED
    assert math.isclose(result.result["x"][0], 0.5, abs_tol=1e-6)
    assert math.isclose(result.result["x"][1], 0.5, abs_tol=1e-6)
    assert result.result["method"] == "SLSQP"
    assert result.diagnostics["converged"] is True


def test_optimize_constrained_schema_violation_is_invalid_without_executing() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_constrained",
            inputs={
                "variables": ["x"],
                "expression": "x**2",
                "x0": [0.0],
                "unexpected_field": True,
            },
        )
    )
    assert result.status is ExecutionStatus.INVALID


def test_optimize_constrained_x0_length_mismatch_is_invalid() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.optimize_constrained",
            inputs={"variables": ["x", "y"], "expression": "x**2 + y**2", "x0": [0.0]},
        )
    )
    assert result.status is ExecutionStatus.INVALID
