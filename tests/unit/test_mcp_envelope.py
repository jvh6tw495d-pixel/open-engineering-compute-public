"""Unit tests for the MCP authoritative-answer envelope (v2.5.3 Wave 1).

Covers extract_executions / build_authoritative_answer / normalize across the
nine live response shapes without requiring an Engine.
"""

from __future__ import annotations

from typing import Any

import pytest

from oec.mcp.envelope import (
    AUTHORITATIVE_ANSWER_SCHEMA_VERSION,
    AuthoritativeAnswer,
    MethodSummary,
    ProblemClassification,
    RouteDecision,
    build_authoritative_answer,
    build_review_authoritative_answer,
    confidence_from_score,
    extract_executions,
    kind_for_skill,
    looks_like_execution,
    normalize,
)


def _execution(
    *,
    status: str = "VALIDATED",
    skill_id: str = "optimization.lp",
    method_id: str = "highs",
    result: dict[str, Any] | None = None,
    run_id: str = "run-1",
    input_hash: str = "hash-1",
    solver_status: str | None = "optimal",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "skill": {"id": skill_id, "version": "0.1.0"},
        "method": {"id": method_id, "version": "0.1.0"},
        "result": result if result is not None else {"objective_value": 42.0},
        "provenance": {"input_hash": input_hash},
        "diagnostics": {},
        "started_at": "2026-07-31T00:00:00Z",
    }
    if solver_status is not None:
        payload["diagnostics"]["solver_status"] = solver_status
    return payload


# ---------------------------------------------------------------------------
# Dataclass to_dict conventions
# ---------------------------------------------------------------------------


def test_dataclass_to_dict_shapes() -> None:
    aa = AuthoritativeAnswer(
        kind="optimization_result", values={"x": 1}, provenance={"run_id": "r"}
    )
    assert aa.to_dict() == {
        "kind": "optimization_result",
        "values": {"x": 1},
        "provenance": {"run_id": "r"},
    }
    pc = ProblemClassification(
        domain="optimization", problem_class="lp", confidence=0.9, reason="ops"
    )
    assert pc.to_dict()["domain"] == "optimization"
    ms = MethodSummary(
        specialist="agent.optimization_specialist",
        skill="optimization.lp",
        backend="highs",
        review_applied=False,
    )
    assert ms.to_dict()["skill"] == "optimization.lp"
    assert AUTHORITATIVE_ANSWER_SCHEMA_VERSION == "1.0"


def test_confidence_from_score_maps_to_unit_interval() -> None:
    assert confidence_from_score(0) == 0.0
    assert confidence_from_score(3) == pytest.approx(1 / 3)
    assert confidence_from_score(9) == 1.0
    assert confidence_from_score(18) == 1.0
    assert confidence_from_score(-1) == 0.0


def test_kind_for_skill_closed_table() -> None:
    assert kind_for_skill("optimization.lp") == "optimization_result"
    assert kind_for_skill("mathematics.solve_root") == "mathematics_result"
    assert kind_for_skill("timeseries.pacf") == "timeseries_result"
    assert kind_for_skill("energy.balance") == "energy_result"
    assert kind_for_skill("battery.soc_step") == "energy_result"
    assert kind_for_skill("control.pid_discrete") == "control_dynamics_result"
    assert kind_for_skill("finance.var") == "finance_uncertainty_result"
    assert kind_for_skill("unknown.foo") == "generic_result"
    assert kind_for_skill(None, specialist="agent.scientific_reviewer") == "review_result"


# ---------------------------------------------------------------------------
# extract_executions — nine shapes
# ---------------------------------------------------------------------------


def test_extract_shape_1_needs_clarification_empty() -> None:
    payload = {
        "status": "needs_clarification",
        "request": "hello",
        "candidate_domains": [],
        "questions": [],
    }
    assert extract_executions(payload) == []


def test_extract_shape_2_needs_more_information_empty() -> None:
    payload = {
        "status": "needs_more_information",
        "agent": "agent.time_series",
        "request": "resample this",
        "candidates": [],
    }
    assert extract_executions(payload) == []


def test_extract_shape_3_specialist_report_execution() -> None:
    ex = _execution()
    payload = {
        "problem_class": "lp",
        "skill_id": "optimization.lp",
        "ops": {},
        "execution": ex,
        "narrative": "ok",
    }
    assert extract_executions(payload) == [ex]


def test_extract_shape_3_null_execution() -> None:
    payload = {
        "problem_class": "out_of_scope",
        "skill_id": None,
        "execution": None,
        "narrative": "",
    }
    assert extract_executions(payload) == []


def test_extract_shape_4_skill_agent_report() -> None:
    ex = _execution(skill_id="timeseries.resample", method_id="kernel")
    payload = {
        "agent": "time_series_specialist",
        "skill_id": "timeseries.resample",
        "inputs": {},
        "execution": ex,
        "narrative": "ok",
        "notes": [],
    }
    assert extract_executions(payload) == [ex]


def test_extract_shape_5_math_min_max_executions() -> None:
    min_ex = _execution(
        skill_id="mathematics.optimize_scalar",
        method_id="scipy_bounded",
        result={"x": 1.0, "fun": 0.0},
        run_id="min-run",
    )
    max_ex = _execution(
        skill_id="mathematics.optimize_scalar",
        method_id="scipy_bounded",
        result={"x": 5.0, "fun": -10.0},
        run_id="max-run",
    )
    payload = {
        "agent": "applied_mathematics_specialist",
        "request": "extrema",
        "interpreted_as": "scalar_extrema_on_closed_interval",
        "min_execution": min_ex,
        "max_execution": max_ex,
        "narrative": "ok",
    }
    assert extract_executions(payload) == [min_ex, max_ex]


def test_extract_shape_6_review_report_empty() -> None:
    payload = {
        "passed": True,
        "checks": [{"code": "objective_match", "ok": True, "message": "ok", "severity": "error"}],
    }
    assert extract_executions(payload) == []
    assert looks_like_execution(payload) is False


def test_extract_shape_7_router_wrapper_recurses() -> None:
    ex = _execution()
    payload = {
        "router": "agent.default",
        "selected_agent": "agent.optimization_specialist",
        "request": "solve",
        "result": {
            "problem_class": "lp",
            "skill_id": "optimization.lp",
            "execution": ex,
        },
    }
    assert extract_executions(payload) == [ex]


def test_extract_shape_7_router_wrapping_needs_more_information() -> None:
    payload = {
        "router": "agent.default",
        "selected_agent": "agent.optimization_specialist",
        "result": {
            "status": "needs_more_information",
            "agent": "agent.optimization_specialist",
            "candidates": [],
        },
    }
    assert extract_executions(payload) == []


def test_extract_shape_8_bare_execution_result() -> None:
    ex = _execution(skill_id="mathematics.solve_root", result={"root": 1.414})
    assert extract_executions(ex) == [ex]


def test_extract_shape_9_structured_error_empty() -> None:
    payload = {"error": "boom", "details": {"tool": "agent.default", "error_type": "ValueError"}}
    assert extract_executions(payload) == []


# ---------------------------------------------------------------------------
# build_authoritative_answer
# ---------------------------------------------------------------------------


def test_build_authoritative_answer_single_optimization_verbatim_values() -> None:
    result_body = {"objective_value": 7.5, "x": {"a": 1.0}}
    ex = _execution(result=result_body)
    aa = build_authoritative_answer([ex], "agent.optimization_specialist")
    assert aa is not None
    assert aa.kind == "optimization_result"
    assert aa.values == result_body
    assert aa.values is not result_body  # defensive copy
    assert aa.provenance["run_id"] == "run-1"
    assert aa.provenance["input_hash"] == "hash-1"
    assert aa.provenance["solver_status"] == "optimal"


def test_build_authoritative_answer_omits_invalid_and_failed() -> None:
    assert (
        build_authoritative_answer([_execution(status="INVALID")], "agent.optimization_specialist")
        is None
    )
    assert (
        build_authoritative_answer([_execution(status="FAILED")], "agent.optimization_specialist")
        is None
    )
    assert build_authoritative_answer([], "agent.optimization_specialist") is None


def test_build_authoritative_answer_keeps_approximate_and_inconclusive() -> None:
    for status in ("APPROXIMATE", "INCONCLUSIVE", "CONVERGED_WITH_WARNINGS", "VERIFIED"):
        aa = build_authoritative_answer(
            [_execution(status=status)], "agent.optimization_specialist"
        )
        assert aa is not None, status
        assert aa.kind == "optimization_result"


def test_build_authoritative_answer_scalar_extrema_dual() -> None:
    min_ex = _execution(
        skill_id="mathematics.optimize_scalar",
        result={"x": 2.0, "fun": 1.0},
        run_id="min-run",
    )
    max_ex = _execution(
        skill_id="mathematics.optimize_scalar",
        result={"x": 5.0, "fun": -9.0},
        run_id="max-run",
    )
    aa = build_authoritative_answer(
        [min_ex, max_ex],
        "agent.applied_mathematics",
        report={"interpreted_as": "scalar_extrema_on_closed_interval"},
    )
    assert aa is not None
    assert aa.kind == "scalar_extrema_result"
    assert aa.values == {
        "min": {"x": 2.0, "fun": 1.0},
        "max": {"x": 5.0, "fun": -9.0},
    }
    assert aa.provenance["min_run_id"] == "min-run"
    assert aa.provenance["max_run_id"] == "max-run"


def test_build_review_authoritative_answer() -> None:
    report = {
        "passed": True,
        "checks": [{"code": "c1", "ok": True, "message": "ok", "severity": "error"}],
    }
    aa = build_review_authoritative_answer(report)
    assert aa.kind == "review_result"
    assert aa.values["passed"] is True
    assert aa.values["checks"] == report["checks"]


# ---------------------------------------------------------------------------
# normalize — additive, passthrough, idempotent
# ---------------------------------------------------------------------------


def test_normalize_passthrough_needs_clarification() -> None:
    payload = {
        "status": "needs_clarification",
        "request": "vague",
        "router": "agent.default",
        "reason": "intent_absent",
        "questions": [],
    }
    out = normalize(payload, tool_name="agent.default", decision=None)
    assert out is payload or out == payload
    assert "authoritative_answer" not in out
    assert out["status"] == "needs_clarification"


def test_normalize_passthrough_needs_more_information() -> None:
    payload = {
        "status": "needs_more_information",
        "agent": "agent.time_series",
        "candidates": [{"skill_id": "timeseries.resample"}],
    }
    out = normalize(payload, tool_name="agent.time_series")
    assert out["status"] == "needs_more_information"
    assert "authoritative_answer" not in out


def test_normalize_passthrough_structured_error() -> None:
    payload = {"error": "nope", "details": {"tool": "agent.default"}}
    out = normalize(payload, tool_name="agent.default")
    assert out == payload
    assert "authoritative_answer" not in out


def test_normalize_direct_optimization_adds_authority_additively() -> None:
    ex = _execution(result={"objective_value": 1.0, "x": {"a": 1}})
    payload = {
        "problem_class": "lp",
        "skill_id": "optimization.lp",
        "execution": ex,
        "narrative": "from ExecutionResult only",
    }
    decision = RouteDecision(
        target="agent.optimization_specialist",
        confidence=1.0,
        reason="direct specialist call",
        signal="direct",
    )
    out = normalize(
        payload,
        tool_name="agent.optimization_specialist",
        decision=decision,
    )
    # Existing keys preserved.
    assert out["problem_class"] == "lp"
    assert out["execution"] is ex or out["execution"] == ex
    assert out["status"] == "ok"
    assert out["authoritative_answer_schema_version"] == "1.0"
    aa = out["authoritative_answer"]
    assert aa["kind"] == "optimization_result"
    assert aa["values"] == {"objective_value": 1.0, "x": {"a": 1}}
    assert out["problem_classification"]["domain"] == "optimization"
    assert out["problem_classification"]["problem_class"] == "lp"
    assert out["method_summary"]["skill"] == "optimization.lp"
    assert out["method_summary"]["backend"] == "highs"
    assert out["narrative"] == "from ExecutionResult only"


def test_normalize_router_preserves_result_nesting() -> None:
    ex = _execution()
    payload = {
        "router": "agent.default",
        "selected_agent": "agent.optimization_specialist",
        "request": "solve",
        "result": {
            "problem_class": "lp",
            "skill_id": "optimization.lp",
            "execution": ex,
        },
    }
    decision = RouteDecision(
        target="agent.optimization_specialist",
        confidence=0.67,
        reason="matched: optimization",
        signal="request_intent",
    )
    out = normalize(payload, tool_name="agent.default", decision=decision)
    # Nesting preserved for existing tests that read payload["result"][...].
    assert out["result"]["skill_id"] == "optimization.lp"
    assert out["result"]["execution"]["status"] == "VALIDATED"
    assert out["authoritative_answer"]["kind"] == "optimization_result"
    assert out["selected_agent"] == "agent.optimization_specialist"


def test_normalize_router_nested_needs_more_information_has_no_authority() -> None:
    payload = {
        "router": "agent.default",
        "selected_agent": "agent.optimization_specialist",
        "result": {
            "status": "needs_more_information",
            "agent": "agent.optimization_specialist",
            "candidates": [],
        },
    }
    out = normalize(
        payload,
        tool_name="agent.default",
        decision=RouteDecision(
            target="agent.optimization_specialist",
            confidence=1.0,
            reason="preferred_domain",
            signal="preferred_domain",
        ),
    )
    assert "authoritative_answer" not in out
    assert out["result"]["status"] == "needs_more_information"
    assert out.get("status") != "ok"


def test_normalize_review_report_authority() -> None:
    payload = {
        "passed": True,
        "checks": [{"code": "c1", "ok": True, "message": "ok", "severity": "error"}],
    }
    out = normalize(payload, tool_name="agent.scientific_reviewer")
    assert out["status"] == "ok"
    assert out["authoritative_answer"]["kind"] == "review_result"
    assert out["authoritative_answer"]["values"]["passed"] is True
    assert out["passed"] is True  # original keys preserved


def test_normalize_failed_execution_omits_authoritative_answer() -> None:
    payload = {
        "agent": "applied_mathematics_specialist",
        "skill_id": "mathematics.solve_root",
        "execution": _execution(status="FAILED", skill_id="mathematics.solve_root"),
    }
    out = normalize(payload, tool_name="agent.applied_mathematics")
    assert out["status"] == "ok"
    assert "authoritative_answer" not in out
    assert out["method_summary"]["skill"] == "mathematics.solve_root"


def test_normalize_idempotent() -> None:
    payload = {
        "problem_class": "lp",
        "skill_id": "optimization.lp",
        "execution": _execution(),
    }
    once = normalize(payload, tool_name="agent.optimization_specialist")
    twice = normalize(once, tool_name="agent.optimization_specialist")
    assert twice == once


def test_normalize_math_extrema_kind() -> None:
    payload = {
        "agent": "applied_mathematics_specialist",
        "interpreted_as": "scalar_extrema_on_closed_interval",
        "min_execution": _execution(
            skill_id="mathematics.optimize_scalar",
            result={"x": 1.0, "fun": 0.0},
            run_id="min",
        ),
        "max_execution": _execution(
            skill_id="mathematics.optimize_scalar",
            result={"x": 2.0, "fun": -1.0},
            run_id="max",
        ),
    }
    out = normalize(payload, tool_name="agent.applied_mathematics")
    assert out["authoritative_answer"]["kind"] == "scalar_extrema_result"
    assert set(out["authoritative_answer"]["values"]) == {"min", "max"}
