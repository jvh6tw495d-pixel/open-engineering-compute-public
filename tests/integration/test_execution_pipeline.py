"""End-to-end: real subprocess execution of the mathematics.identity fixture
skill through the full ExecutionService pipeline, checked against a golden
case (plan section 12.6)."""

from pathlib import Path

from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry
from oec.validation.golden import GoldenCase, assert_matches_golden

_FIXTURES_ROOT = Path("tests/fixtures/skills")

_IDENTITY_GOLDEN = GoldenCase(
    id="identity-basic",
    skill_id="mathematics.identity",
    skill_version="0.1.0",
    inputs={"value": 42},
    expected_result={"value": 42.0},
    source="trivial by construction: f(x) = x",
    justification="the identity skill has no methodology to verify beyond passthrough",
)


def test_identity_skill_executes_end_to_end_and_matches_its_golden_case() -> None:
    registry = SkillRegistry()
    report = registry.register_all(_FIXTURES_ROOT)
    assert not report.failures, f"fixture skills failed to load: {report.failures}"

    service = ExecutionService(registry)
    result = service.execute(
        ExecutionRequest(skill_id=_IDENTITY_GOLDEN.skill_id, inputs=_IDENTITY_GOLDEN.inputs)
    )

    assert result.status is ExecutionStatus.VERIFIED
    assert_matches_golden(result.result, _IDENTITY_GOLDEN)


def test_identity_skill_result_carries_full_provenance() -> None:
    registry = SkillRegistry()
    registry.register_all(_FIXTURES_ROOT)
    service = ExecutionService(registry)

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1}))

    assert result.skill.id == "mathematics.identity"
    assert result.skill.version == "0.1.0"
    assert result.method.id == "identity"
    assert result.provenance["sandbox"]["timeout_enforced"] is True
    assert result.started_at <= result.completed_at  # type: ignore[operator]
