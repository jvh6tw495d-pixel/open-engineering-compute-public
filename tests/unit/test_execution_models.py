from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from oec.common import VersionedRef
from oec.execution.models import ExecutionRequest, ExecutionResult, ExecutionStatus


def test_execution_request_generates_trace_id_by_default() -> None:
    req1 = ExecutionRequest(skill_id="electrical.voltage_drop", inputs={"voltage": 380})
    req2 = ExecutionRequest(skill_id="electrical.voltage_drop", inputs={"voltage": 380})
    assert req1.trace_id != req2.trace_id
    assert req1.skill_version is None
    assert req1.seed is None
    assert req1.options == {}


def test_execution_request_is_frozen() -> None:
    req = ExecutionRequest(skill_id="electrical.voltage_drop", inputs={})
    with pytest.raises(ValidationError):
        req.seed = 42  # type: ignore[misc]


def test_execution_result_requires_status_skill_and_method() -> None:
    with pytest.raises(ValidationError):
        ExecutionResult(started_at=datetime.now(UTC))  # type: ignore[call-arg]


def test_execution_result_has_no_boolean_success_field() -> None:
    assert "success" not in ExecutionResult.model_fields


def test_execution_result_generates_unique_run_ids() -> None:
    skill = VersionedRef(id="electrical.voltage_drop", version="0.1.0")
    method = VersionedRef(id="three_phase_impedance_voltage_drop", version="0.1.0")
    result1 = ExecutionResult(
        status=ExecutionStatus.VALIDATED,
        skill=skill,
        method=method,
        started_at=datetime.now(UTC),
    )
    result2 = ExecutionResult(
        status=ExecutionStatus.VALIDATED,
        skill=skill,
        method=method,
        started_at=datetime.now(UTC),
    )
    assert result1.run_id != result2.run_id


def test_execution_status_covers_the_full_graded_spectrum() -> None:
    expected = {
        "VERIFIED",
        "VALIDATED",
        "CONVERGED_WITH_WARNINGS",
        "APPROXIMATE",
        "INCONCLUSIVE",
        "INVALID",
        "FAILED",
    }
    assert {status.value for status in ExecutionStatus} == expected
