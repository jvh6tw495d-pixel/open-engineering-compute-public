from pathlib import Path
from typing import Any, ClassVar

from _skill_helpers import write_skill_dir
from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.loader.models import LoadedSkill
from oec.skills.registry.registry import SkillRegistry
from oec.validation.base import Severity, ValidationOutcome


class _FakeInputValidator:
    layer: ClassVar[str] = "fake_input"

    def __init__(self, outcomes: list[ValidationOutcome]) -> None:
        self._outcomes = outcomes

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        return self._outcomes


class _CrashingInputValidator:
    layer: ClassVar[str] = "crashing_input"

    def validate(
        self, skill: LoadedSkill, normalized_inputs: dict[str, Any]
    ) -> list[ValidationOutcome]:
        raise RuntimeError("boom from a buggy input validator")


class _CrashingResultValidator:
    layer: ClassVar[str] = "crashing_result"

    def validate(
        self,
        skill: LoadedSkill,
        normalized_inputs: dict[str, Any],
        result: dict[str, Any],
        diagnostics: dict[str, Any],
    ) -> list[ValidationOutcome]:
        raise RuntimeError("boom from a buggy result validator")


class _FakeResultValidator:
    layer: ClassVar[str] = "fake_result"

    def __init__(self, outcomes: list[ValidationOutcome]) -> None:
        self._outcomes = outcomes

    def validate(
        self,
        skill: LoadedSkill,
        normalized_inputs: dict[str, Any],
        result: dict[str, Any],
        diagnostics: dict[str, Any],
    ) -> list[ValidationOutcome]:
        return self._outcomes


def _registry_with_identity(tmp_path: Path, **write_kwargs: Any) -> SkillRegistry:
    write_skill_dir(tmp_path, **write_kwargs)
    registry = SkillRegistry()
    registry.register_all(tmp_path)
    return registry


def test_successful_execution_is_verified(tmp_path: Path) -> None:
    registry = _registry_with_identity(tmp_path)
    service = ExecutionService(registry)
    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 5}))

    assert result.status is ExecutionStatus.VERIFIED
    assert result.result == {"value": 5}
    assert result.skill.id == "mathematics.identity"
    assert result.method.id == "identity"
    assert result.run_id
    assert result.duration_ms is not None and result.duration_ms >= 0


def test_input_validator_error_yields_invalid_without_executing(tmp_path: Path) -> None:
    marker = tmp_path / "should_not_run"
    registry = _registry_with_identity(
        tmp_path,
        implementation_code=(
            f"from pathlib import Path\n"
            f"def execute(inputs):\n"
            f"    Path(r'{marker}').write_text('ran')\n"
            f"    return {{'result': {{}}, 'diagnostics': {{}}}}\n"
        ),
    )
    error_outcome = ValidationOutcome(layer="schema", severity=Severity.ERROR, messages=["bad"])
    service = ExecutionService(registry, input_validators=[_FakeInputValidator([error_outcome])])

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={}))

    assert result.status is ExecutionStatus.INVALID
    assert not marker.exists(), "implementation must not run when an input validator errors"


def test_input_validator_warning_yields_converged_with_warnings(tmp_path: Path) -> None:
    registry = _registry_with_identity(tmp_path)
    warning_outcome = ValidationOutcome(
        layer="physical", severity=Severity.WARNING, messages=["near limit"]
    )
    service = ExecutionService(registry, input_validators=[_FakeInputValidator([warning_outcome])])

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1}))

    assert result.status is ExecutionStatus.CONVERGED_WITH_WARNINGS
    assert result.warnings == ["near limit"]


def test_result_validator_runs_after_execution(tmp_path: Path) -> None:
    registry = _registry_with_identity(tmp_path)
    error_outcome = ValidationOutcome(
        layer="invariants", severity=Severity.ERROR, messages=["NaN in result"]
    )
    service = ExecutionService(registry, result_validators=[_FakeResultValidator([error_outcome])])

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1}))

    assert result.status is ExecutionStatus.INVALID
    assert result.result == {"value": 1}, "result validators see the real result, not an empty one"


def test_crashing_input_validator_fails_closed_not_the_whole_service(tmp_path: Path) -> None:
    """A buggy validator must not crash ExecutionService -- it becomes an
    ERROR-severity outcome (fail closed), found in the Sprint 03 review."""
    registry = _registry_with_identity(tmp_path)
    service = ExecutionService(registry, input_validators=[_CrashingInputValidator()])

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1}))

    assert result.status is ExecutionStatus.INVALID
    outcomes = result.validation["outcomes"]
    assert any(o["layer"] == "crashing_input" and "boom" in o["messages"][0] for o in outcomes)


def test_crashing_result_validator_fails_closed_not_the_whole_service(tmp_path: Path) -> None:
    registry = _registry_with_identity(tmp_path)
    service = ExecutionService(registry, result_validators=[_CrashingResultValidator()])

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1}))

    assert result.status is ExecutionStatus.INVALID
    outcomes = result.validation["outcomes"]
    assert any(o["layer"] == "crashing_result" and "boom" in o["messages"][0] for o in outcomes)


def test_implementation_crash_yields_failed(tmp_path: Path) -> None:
    registry = _registry_with_identity(
        tmp_path, implementation_code="def execute(inputs):\n    raise ValueError('boom')\n"
    )
    service = ExecutionService(registry)

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={}))

    assert result.status is ExecutionStatus.FAILED
    assert "boom" in result.diagnostics["error_output"]
    assert result.diagnostics["timed_out"] is False


def test_timeout_yields_failed(tmp_path: Path) -> None:
    registry = _registry_with_identity(
        tmp_path,
        manifest_overrides={"execution": {"timeout_seconds": 1}},
        implementation_code=(
            "import time\n"
            "def execute(inputs):\n"
            "    time.sleep(10)\n"
            "    return {'result': {}, 'diagnostics': {}}\n"
        ),
    )
    service = ExecutionService(registry)

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={}))

    assert result.status is ExecutionStatus.FAILED
    assert result.diagnostics["timed_out"] is True


def test_converged_iterative_method_is_validated(tmp_path: Path) -> None:
    registry = _registry_with_identity(
        tmp_path,
        manifest_overrides={"method": {"id": "identity", "version": "1", "iterative": True}},
        implementation_code=(
            "def execute(inputs):\n"
            "    return {'result': {'value': 1}, 'diagnostics': {'converged': True}}\n"
        ),
    )
    service = ExecutionService(registry)

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={}))

    assert result.status is ExecutionStatus.VALIDATED


def test_non_converged_iterative_method_is_inconclusive(tmp_path: Path) -> None:
    registry = _registry_with_identity(
        tmp_path,
        manifest_overrides={"method": {"id": "identity", "version": "1", "iterative": True}},
        implementation_code=(
            "def execute(inputs):\n"
            "    return {'result': {'value': 1}, 'diagnostics': {'converged': False}}\n"
        ),
    )
    service = ExecutionService(registry)

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={}))

    assert result.status is ExecutionStatus.INCONCLUSIVE


def test_iterative_method_omitting_converged_is_a_contract_violation(tmp_path: Path) -> None:
    """ADR 0013: an iterative method that doesn't report diagnostics['converged']
    must never be silently treated as VERIFIED -- it's a FAILED contract violation."""
    registry = _registry_with_identity(
        tmp_path,
        manifest_overrides={"method": {"id": "identity", "version": "1", "iterative": True}},
        implementation_code=(
            "def execute(inputs):\n    return {'result': {'value': 1}, 'diagnostics': {}}\n"
        ),
    )
    service = ExecutionService(registry)

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={}))

    assert result.status is ExecutionStatus.FAILED
    assert "converged" in result.diagnostics["error_output"]


def test_provenance_reports_the_sandbox_honestly(tmp_path: Path) -> None:
    registry = _registry_with_identity(tmp_path)
    service = ExecutionService(registry)

    result = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1}))

    assert result.provenance["sandbox"] == {
        "timeout_enforced": True,
        "network_isolation_enforced": False,
        "filesystem_isolation_enforced": False,
        "memory_limit_enforced": False,
    }
    assert result.provenance["trace_id"] == result.provenance["trace_id"]  # present, non-empty
    assert result.provenance["trace_id"]


def test_run_id_is_unique_across_executions(tmp_path: Path) -> None:
    registry = _registry_with_identity(tmp_path)
    service = ExecutionService(registry)

    first = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1}))
    second = service.execute(ExecutionRequest(skill_id="mathematics.identity", inputs={"value": 1}))

    assert first.run_id != second.run_id
