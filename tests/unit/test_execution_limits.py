"""Phase A2: input payload / sequence / depth limits."""

from pathlib import Path

from oec.execution.limits import (
    DEFAULT_MAX_SEQUENCE_LENGTH,
    InputLimits,
    check_input_limits,
)
from oec.execution.models import ExecutionRequest, ExecutionStatus
from oec.execution.service import ExecutionService
from oec.skills.registry.registry import SkillRegistry
from oec.testing import write_skill_dir
from oec.validation.base import Severity


def test_check_input_limits_accepts_small_payload() -> None:
    outcomes = check_input_limits({"x": 1, "y": [1, 2, 3]})
    assert outcomes == []


def test_check_input_limits_rejects_oversized_json() -> None:
    limits = InputLimits(max_input_json_bytes=50)
    outcomes = check_input_limits({"blob": "x" * 200}, limits)
    assert any(o.severity is Severity.ERROR for o in outcomes)
    assert any(o.details.get("limit") == "max_input_json_bytes" for o in outcomes)


def test_check_input_limits_rejects_long_sequence() -> None:
    limits = InputLimits(max_sequence_length=10)
    outcomes = check_input_limits({"xs": list(range(20))}, limits)
    assert any(o.details.get("limit") == "max_sequence_length" for o in outcomes)


def test_check_input_limits_rejects_deep_nesting() -> None:
    limits = InputLimits(max_depth=3)
    nested: dict = {"a": {"b": {"c": {"d": 1}}}}
    outcomes = check_input_limits(nested, limits)
    assert any(o.details.get("limit") == "max_depth" for o in outcomes)


def test_execution_service_returns_invalid_on_limit_breach(tmp_path: Path) -> None:
    write_skill_dir(tmp_path)
    registry = SkillRegistry()
    registry.register_all(tmp_path)
    service = ExecutionService(
        registry,
        input_limits=InputLimits(max_sequence_length=5),
    )
    result = service.execute(
        ExecutionRequest(
            skill_id="mathematics.identity",
            inputs={"value": 1, "pad": list(range(20))},
        )
    )
    assert result.status is ExecutionStatus.INVALID
    assert result.result == {}
    outcomes = result.validation["outcomes"]
    assert any(o["layer"] == "limits" for o in outcomes)
    assert any("max_sequence_length" in m for o in outcomes for m in o["messages"])
    assert result.provenance["input_hash"]


def test_default_sequence_limit_is_documented_constant() -> None:
    assert DEFAULT_MAX_SEQUENCE_LENGTH == 100_000
