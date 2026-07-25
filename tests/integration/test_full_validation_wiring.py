"""Proves the Sprint 03 contract actually holds end to end: the concrete
validator layers built independently in the sprint03-validation worktree
(Grok) plug into ExecutionService (built in parallel, this tree) with no
adjustment needed -- both sides only ever depended on
oec.validation.base's frozen protocols.
"""

from pathlib import Path

from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry
from oec.validation.invariants import InvariantValidator
from oec.validation.numerical import NumericalDiagnosticsValidator
from oec.validation.schema import SchemaValidator

_FIXTURES_ROOT = Path("tests/fixtures/skills")


def _service() -> ExecutionService:
    registry = SkillRegistry()
    report = registry.register_all(_FIXTURES_ROOT)
    assert not report.failures
    return ExecutionService(
        registry,
        input_validators=[SchemaValidator()],
        result_validators=[InvariantValidator(), NumericalDiagnosticsValidator()],
    )


def test_valid_input_passes_the_real_schema_validator_and_executes() -> None:
    service = _service()
    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 7}))
    assert result.status is ExecutionStatus.VERIFIED
    assert result.result == {"value": 7}


def test_schema_violation_is_caught_before_execution() -> None:
    service = _service()
    # "value" must be a number per input.schema.json; additionalProperties is false.
    result = service.execute(
        ExecutionRequest(skill_id="mathematics.identity", inputs={"value": "not a number"})
    )
    assert result.status is ExecutionStatus.INVALID
    outcomes = result.validation["outcomes"]
    assert any(o["layer"] == "schema" for o in outcomes)


def test_missing_required_field_is_caught_by_the_real_schema_validator() -> None:
    service = _service()
    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={}))
    assert result.status is ExecutionStatus.INVALID


def test_additional_property_is_rejected_by_the_real_schema_validator() -> None:
    service = _service()
    result = service.execute(
        ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1, "extra": True})
    )
    assert result.status is ExecutionStatus.INVALID
