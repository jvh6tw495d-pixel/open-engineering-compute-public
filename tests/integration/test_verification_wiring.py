"""Proves the Verification Engine (ADR 0021) is wired into ExecutionService
end to end, additively: ExecutionResult's required top-level shape
(tests/integration/test_execution_result_contract.py) is unaffected, and
validation["verification"] carries the structured pre/post report.
"""

from pathlib import Path

from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry
from oec.validation.schema import SchemaValidator

_FIXTURES_ROOT = Path("tests/fixtures/skills")
_REQUIRED_EXECUTION_RESULT_KEYS = frozenset(
    {
        "run_id",
        "status",
        "skill",
        "method",
        "inputs",
        "normalized_inputs",
        "result",
        "assumptions",
        "conventions",
        "diagnostics",
        "validation",
        "warnings",
        "provenance",
        "started_at",
        "completed_at",
        "duration_ms",
    }
)


def _service() -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_FIXTURES_ROOT)
    assert not report.failures
    return ExecutionService(registry, input_validators=[SchemaValidator()])


def test_verification_report_present_on_successful_execution() -> None:
    service = _service()
    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 7}))

    assert result.status is ExecutionStatus.VERIFIED
    dumped = result.model_dump(mode="json")
    missing = _REQUIRED_EXECUTION_RESULT_KEYS - dumped.keys()
    assert not missing, "ExecutionResult shape must be unbroken"

    verification = result.validation["verification"]
    assert "pre" in verification and "post" in verification
    pre_names = {check["name"] for check in verification["pre"]}
    assert {"input_validation", "backend_fit"} <= pre_names
    post_names = {check["name"] for check in verification["post"]}
    assert {"residuals_and_conditioning", "lp_gap", "reproducibility"} <= post_names


def test_verification_pre_check_reflects_input_error_without_executing() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(skill_id="mathematics.identity", inputs={"value": "not a number"})
    )

    assert result.status is ExecutionStatus.INVALID
    verification = result.validation["verification"]
    pre_by_name = {check["name"]: check for check in verification["pre"]}
    assert pre_by_name["input_validation"]["passed"] is False
    assert verification["post"] == [], "no post-checks when the implementation never ran"


def test_outcomes_key_is_still_present_alongside_verification() -> None:
    service = _service()
    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1}))
    assert "outcomes" in result.validation
    assert "verification" in result.validation
