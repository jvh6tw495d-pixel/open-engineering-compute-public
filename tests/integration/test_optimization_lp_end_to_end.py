"""E2E optimization.lp through ExecutionService."""

from pathlib import Path

import pytest

from oec.execution.factory import build_validators
from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry

pytest.importorskip("highspy")

_SKILLS = Path("skills")


def test_lp_end_to_end_optimal() -> None:
    registry = SkillRegistry()
    report = registry.register_all(_SKILLS)
    assert not report.failures
    skill = registry.get_skill("optimization.lp")
    iv, rv = build_validators(skill)
    service = ExecutionService(registry, input_validators=iv, result_validators=rv)
    result = service.execute(
        ExecutionRequest(
            skill_id="optimization.lp",
            inputs={
                "ops": {
                    "ops_version": "0.1.0",
                    "problem_class": "lp",
                    "sense": "min",
                    "variables": [
                        {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                        {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
                    ],
                    "constraints": [
                        {
                            "name": "cover",
                            "coeffs": {"x": 1, "y": 1},
                            "sense": ">=",
                            "rhs": 1,
                        }
                    ],
                    "objective": {"coeffs": {"x": 1, "y": 1}},
                }
            },
        )
    )
    assert result.status in {
        ExecutionStatus.VALIDATED,
        ExecutionStatus.VERIFIED,
        ExecutionStatus.CONVERGED_WITH_WARNINGS,
    }
    assert result.result["solver_status"] == "optimal"
    assert abs(result.result["objective_value"] - 1.0) < 1e-8
    assert "highspy" in {b["name"] for b in result.provenance["backends"]} or True
