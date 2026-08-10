"""Agent narrative authority: no number / claim without run_id."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from agents.common import (
    assert_narrative_authority,
    narrate_execution,
    narrative_authority_violations,
    narrative_cites_run_id,
)

from oec.common import VersionedRef
from oec.execution.models import ExecutionResult, ExecutionStatus


def _er(
    *,
    run_id: str = "run-auth-001",
    result: dict | None = None,
    status: ExecutionStatus = ExecutionStatus.VALIDATED,
) -> ExecutionResult:
    return ExecutionResult(
        run_id=run_id,
        status=status,
        skill=VersionedRef(id="mathematics.optimize_scalar", version="1.0.0"),
        method=VersionedRef(id="scipy.minimize_scalar", version="1.0.0"),
        result=result or {"x": 1.5, "fun": 0.25},
        provenance={"input_hash": "abc123def456"},
        started_at=datetime(2026, 8, 2, tzinfo=UTC),
    )


def test_narrative_cites_run_id() -> None:
    assert narrative_cites_run_id("result=1 run_id: run-auth-001 done", "run-auth-001")
    assert not narrative_cites_run_id("objective is 0.25", "run-auth-001")
    assert not narrative_cites_run_id("", "run-auth-001")
    assert not narrative_cites_run_id("run_id: something", "")


def test_narrate_execution_always_includes_run_id() -> None:
    er = _er()
    text = narrate_execution("test_agent", er)
    assert er.run_id in text
    assert "run_id:" in text
    assert "1.5" in text or "0.25" in text
    assert_narrative_authority(text, er)


def test_missing_run_id_is_violation() -> None:
    er = _er()
    bad = "The optimum is 0.25 at x=1.5 (trust me)."
    viol = narrative_authority_violations(bad, er)
    assert any("missing run_id" in v for v in viol)
    with pytest.raises(AssertionError, match="run_id"):
        assert_narrative_authority(bad, er)


def test_invented_number_is_violation() -> None:
    er = _er(result={"x": 1.0, "fun": 0.0})
    # Includes run_id but invents a number not in ExecutionResult
    forged = f"run_id: {er.run_id}\nobjective=999.123 (claimed)"
    viol = narrative_authority_violations(forged, er)
    assert any("invented" in v for v in viol)


def test_small_invented_int_not_laundered_by_version() -> None:
    """Version v1.0.0 must not allow invented token '7' via allowlist expansion."""
    er = _er(result={"x": 1.0, "fun": 0.0})
    forged = f"run_id: {er.run_id}\nI claim the optimum is 7 units."
    viol = narrative_authority_violations(forged, er)
    assert any("invented" in v for v in viol)
    assert any("7" in v for v in viol)


def test_import_error_fail_closed() -> None:
    """Missing benchmarks module must not silently skip invented-number checks."""
    import sys

    er = _er()
    narrative = f"run_id: {er.run_id}\nresult: {{'x': 1.5}}"
    saved = sys.modules.get("benchmarks.agent_metrics")
    # Per importlib: None in sys.modules → ImportError/ModuleNotFoundError
    sys.modules["benchmarks.agent_metrics"] = None  # type: ignore[assignment]
    try:
        viol = narrative_authority_violations(narrative, er)
    finally:
        if saved is not None:
            sys.modules["benchmarks.agent_metrics"] = saved
        else:
            sys.modules.pop("benchmarks.agent_metrics", None)
    assert any("benchmarks.agent_metrics unavailable" in v for v in viol)
