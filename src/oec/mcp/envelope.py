"""Authoritative-answer envelope for MCP agent-tool responses (v2.5.3 Wave 1).

Pure functions over plain dicts — no pydantic models, no imports from
``agents/``. The envelope is assembled once at the ``call_tool`` boundary so
routed and direct specialist paths share one host-facing contract without
double-wrapping (``agent.default`` recurses into specialists).

Normalization is **additive**: existing nesting (including
``payload["result"]`` for the router) is preserved; normalized keys are
mirrored at the top level.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

AUTHORITATIVE_ANSWER_SCHEMA_VERSION = "1.1"

# ExecutionStatus values that must never mint an authoritative_answer.
_AUTHORITY_BLOCKED_STATUSES = frozenset({"INVALID", "FAILED"})

# Closed kind taxonomy v1.1 — longest / most-specific prefixes first.
# Additive over v1.0: existing energy_result prefixes for electrical./battery./
# energy. are unchanged; thermal./mechanics./fluids./materials. map to the new
# physics_result kind (schema 1.1 / D3). electrical.* deliberately stays on
# energy_result for host compatibility (classic electrical + dc_power_flow).
_KIND_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("optimization.", "optimization_result"),
    ("timeseries.", "timeseries_result"),
    ("energy.", "energy_result"),
    ("battery.", "energy_result"),
    ("electrical.", "energy_result"),
    ("thermal.", "physics_result"),
    ("mechanics.", "physics_result"),
    ("fluids.", "physics_result"),
    ("materials.", "physics_result"),
    ("control.", "control_dynamics_result"),
    ("dynamics.", "control_dynamics_result"),
    ("finance.", "finance_uncertainty_result"),
    ("uncertainty.", "finance_uncertainty_result"),
    ("mathematics.", "mathematics_result"),
    ("linear.", "linear_result"),
    ("statistics.", "statistics_result"),
    ("numerical.", "numerical_result"),
)

_EXECUTION_SHAPE_KEYS = ("status", "skill", "method", "started_at")


@dataclass
class AuthoritativeAnswer:
    """Host-facing numerical (or review) truth for a solved agent task."""

    kind: str
    values: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the wire shape mirrored onto ``authoritative_answer``."""
        return {
            "kind": self.kind,
            "values": self.values,
            "provenance": self.provenance,
        }


@dataclass
class ProblemClassification:
    """What OEC thinks the problem is (non-authoritative explanation)."""

    domain: str
    problem_class: str | None = None
    confidence: float = 1.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the wire shape mirrored onto ``problem_classification``."""
        return {
            "domain": self.domain,
            "problem_class": self.problem_class,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class MethodSummary:
    """What OEC actually ran (non-authoritative explanation)."""

    specialist: str
    skill: str | None = None
    backend: str | None = None
    review_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return the wire shape mirrored onto ``method_summary``."""
        return {
            "specialist": self.specialist,
            "skill": self.skill,
            "backend": self.backend,
            "review_applied": self.review_applied,
        }


@dataclass(frozen=True)
class RouteDecision:
    """Routing outcome with confidence / reason derived from discovery signals."""

    target: str
    confidence: float
    reason: str
    signal: str


def confidence_from_score(score: int | float) -> float:
    """Map ``rank_domain_intents`` integer scores onto ``[0, 1]``.

    Domain intents score in steps of 3 (token match) or 6 (multi-word alias).
    A score of 9 (three solid token matches, or one alias + one token) maps
    to full confidence; higher scores clamp at 1.0.
    """
    try:
        numeric = float(score)
    except (TypeError, ValueError):
        return 0.0
    if numeric <= 0:
        return 0.0
    return min(1.0, numeric / 9.0)


def looks_like_execution(payload: dict[str, Any]) -> bool:
    """True when ``payload`` has the required ExecutionResult wire keys."""
    return isinstance(payload, dict) and all(key in payload for key in _EXECUTION_SHAPE_KEYS)


def kind_for_skill(skill_id: str | None, *, specialist: str | None = None) -> str:
    """Closed prefix → kind table with ``generic_result`` fallback."""
    if isinstance(skill_id, str) and skill_id:
        for prefix, kind in _KIND_BY_PREFIX:
            if skill_id.startswith(prefix):
                return kind
    if specialist and "review" in specialist:
        return "review_result"
    return "generic_result"


def _skill_id_of(execution: dict[str, Any]) -> str | None:
    skill = execution.get("skill")
    if isinstance(skill, dict):
        skill_id = skill.get("id")
        if isinstance(skill_id, str):
            return skill_id
    return None


def _backend_of(execution: dict[str, Any]) -> str | None:
    method = execution.get("method")
    if isinstance(method, dict):
        method_id = method.get("id")
        if isinstance(method_id, str):
            return method_id
    return None


def _solver_status_of(execution: dict[str, Any]) -> Any:
    diagnostics = execution.get("diagnostics")
    if isinstance(diagnostics, dict) and "solver_status" in diagnostics:
        return diagnostics["solver_status"]
    return execution.get("status")


def _is_authority_blocked(execution: dict[str, Any]) -> bool:
    status = execution.get("status")
    return status in _AUTHORITY_BLOCKED_STATUSES


def _is_review_report(payload: dict[str, Any]) -> bool:
    return (
        isinstance(payload, dict)
        and "passed" in payload
        and "checks" in payload
        and "execution" not in payload
        and "min_execution" not in payload
        and not looks_like_execution(payload)
    )


def _unwrap_report(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the specialist report under a router wrapper, else ``payload``."""
    nested = payload.get("result")
    if (
        isinstance(payload, dict)
        and "router" in payload
        and isinstance(nested, dict)
        and not looks_like_execution(payload)
    ):
        return nested
    return payload


def extract_executions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull ExecutionResult-shaped dicts from any of the nine live MCP shapes.

    Shapes covered:

    1. ``needs_clarification`` — empty
    2. ``needs_more_information`` — empty
    3. ``SpecialistReport`` — ``execution`` (nullable)
    4. ``SkillAgentReport`` — ``execution`` (nullable)
    5. ``MathRequestReport`` — ``min_execution`` + ``max_execution``
    6. ``ReviewReport`` — empty (authority is ``passed`` + ``checks``)
    7. Router wrapper — recurse into ``result``
    8. Bare ``ExecutionResult`` — payload *is* the execution
    9. Structured error — empty
    """
    if not isinstance(payload, dict):
        return []

    # Shape 9: structured tool error body.
    if "error" in payload and not looks_like_execution(payload):
        return []

    # Shapes 1 and 2: routing states with no execution.
    if payload.get("status") in ("needs_clarification", "needs_more_information"):
        return []

    # Shape 7: agent.default router wrapper.
    if (
        "router" in payload
        and isinstance(payload.get("result"), dict)
        and not looks_like_execution(payload)
    ):
        return extract_executions(payload["result"])

    # Shape 5: dual min/max executions (applied-math free-text extrema).
    if "min_execution" in payload or "max_execution" in payload:
        found: list[dict[str, Any]] = []
        for key in ("min_execution", "max_execution"):
            candidate = payload.get(key)
            if isinstance(candidate, dict) and looks_like_execution(candidate):
                found.append(candidate)
        return found

    # Shapes 3 and 4: optional single ``execution`` field.
    if "execution" in payload:
        execution = payload.get("execution")
        if isinstance(execution, dict) and looks_like_execution(execution):
            return [execution]
        return []

    # Shape 6: review report — no execution payload.
    if _is_review_report(payload):
        return []

    # Shape 8: bare ExecutionResult at the top level.
    if looks_like_execution(payload):
        return [payload]

    return []


def build_authoritative_answer(
    executions: list[dict[str, Any]],
    specialist: str,
    *,
    report: dict[str, Any] | None = None,
) -> AuthoritativeAnswer | None:
    """Build an ``AuthoritativeAnswer`` from extracted executions, or ``None``.

    Rules:

    - empty / all-blocked (INVALID/FAILED) → ``None`` (omit the key)
    - dual ``mathematics.optimize_scalar`` (or math free-text extrema report)
      → ``kind: scalar_extrema_result`` with closed ``min``/``max`` values
    - single successful execution → ``values = execution.result`` verbatim
    - kind from skill-id prefix table; fallback ``generic_result``
    """
    if not executions:
        return None

    usable = [ex for ex in executions if not _is_authority_blocked(ex)]
    if not usable:
        return None

    skill_ids = {_skill_id_of(ex) for ex in usable}
    is_scalar_extrema = len(usable) == 2 and (
        skill_ids == {"mathematics.optimize_scalar"}
        or (
            isinstance(report, dict)
            and report.get("interpreted_as") == "scalar_extrema_on_closed_interval"
        )
    )

    if is_scalar_extrema:
        min_ex, max_ex = usable[0], usable[1]
        return AuthoritativeAnswer(
            kind="scalar_extrema_result",
            values={
                "min": dict(min_ex.get("result") or {}),
                "max": dict(max_ex.get("result") or {}),
            },
            provenance={
                "min_run_id": min_ex.get("run_id"),
                "max_run_id": max_ex.get("run_id"),
                "min_input_hash": (min_ex.get("provenance") or {}).get("input_hash"),
                "max_input_hash": (max_ex.get("provenance") or {}).get("input_hash"),
                "min_status": min_ex.get("status"),
                "max_status": max_ex.get("status"),
            },
        )

    execution = usable[0]
    skill_id = _skill_id_of(execution)
    if skill_id is None and isinstance(report, dict):
        maybe = report.get("skill_id")
        if isinstance(maybe, str):
            skill_id = maybe

    return AuthoritativeAnswer(
        kind=kind_for_skill(skill_id, specialist=specialist),
        values=dict(execution.get("result") or {}),
        provenance={
            "run_id": execution.get("run_id"),
            "input_hash": (execution.get("provenance") or {}).get("input_hash"),
            "solver_status": _solver_status_of(execution),
        },
    )


def build_review_authoritative_answer(report: dict[str, Any]) -> AuthoritativeAnswer:
    """Review authority is ``passed`` + ``checks[]`` — never a fake execution."""
    return AuthoritativeAnswer(
        kind="review_result",
        values={
            "passed": report.get("passed"),
            "checks": list(report.get("checks") or []),
        },
        provenance={},
    )


def _domain_for_specialist(specialist: str) -> str:
    mapping = {
        "agent.optimization_specialist": "optimization",
        "agent.scientific_reviewer": "review",
        "agent.applied_mathematics": "mathematics",
        "agent.time_series": "timeseries",
        "agent.energy": "energy",
        "agent.control_dynamics": "control_dynamics",
        "agent.finance_uncertainty": "finance_uncertainty",
        "agent.default": "router",
    }
    return mapping.get(specialist, specialist.removeprefix("agent.") if specialist else "unknown")


def _problem_class_from_report(report: dict[str, Any]) -> str | None:
    problem_class = report.get("problem_class")
    if isinstance(problem_class, str):
        return problem_class
    interpreted = report.get("interpreted_as")
    if isinstance(interpreted, str):
        return interpreted
    return None


def _method_summary_from(
    *,
    specialist: str,
    report: dict[str, Any],
    executions: list[dict[str, Any]],
) -> MethodSummary:
    skill: str | None = None
    if isinstance(report.get("skill_id"), str):
        skill = report["skill_id"]
    elif executions:
        skill = _skill_id_of(executions[0])

    backend: str | None = None
    if executions:
        backend = _backend_of(executions[0])

    return MethodSummary(
        specialist=specialist,
        skill=skill,
        backend=backend,
        review_applied=_is_review_report(report) or "review" in specialist,
    )


def _routing_status(payload: dict[str, Any]) -> str | None:
    """Return needs_* status from top-level or nested router result, else None."""
    status = payload.get("status")
    if isinstance(status, str) and status in (
        "needs_clarification",
        "needs_more_information",
    ):
        return status
    result = payload.get("result")
    if isinstance(result, dict):
        nested = result.get("status")
        if isinstance(nested, str) and nested in (
            "needs_clarification",
            "needs_more_information",
        ):
            return nested
    return None


def normalize(
    payload: dict[str, Any],
    *,
    tool_name: str,
    decision: RouteDecision | None = None,
) -> dict[str, Any]:
    """Additively mirror envelope keys onto an agent-tool payload.

    Passthrough (unchanged) for shapes 1, 2, and 9. Idempotent: a payload
    that already carries ``authoritative_answer_schema_version`` is returned
    as a shallow copy without re-deriving authority.
    """
    if not isinstance(payload, dict):
        return payload

    # Shape 9: structured error — never rewrite.
    if "error" in payload and not looks_like_execution(payload) and "router" not in payload:
        return payload

    # Already normalized (idempotent).
    if payload.get("authoritative_answer_schema_version") == AUTHORITATIVE_ANSWER_SCHEMA_VERSION:
        return dict(payload)

    # Shapes 1 and 2 at top level: pure passthrough.
    if payload.get("status") in ("needs_clarification", "needs_more_information"):
        return payload

    out = dict(payload)
    report = _unwrap_report(payload)
    selected_agent = payload.get("selected_agent")
    selected: str = selected_agent if isinstance(selected_agent, str) else tool_name
    if decision is not None and decision.target:
        selected = decision.target

    # Nested needs_* (router wrapping a suggestion) — no authority, no status:ok.
    if _routing_status(payload) is not None:
        out.setdefault("selected_agent", selected)
        if decision is not None:
            out.setdefault(
                "problem_classification",
                ProblemClassification(
                    domain=_domain_for_specialist(selected),
                    problem_class=None,
                    confidence=decision.confidence,
                    reason=decision.reason,
                ).to_dict(),
            )
        return out

    executions = extract_executions(payload)
    authoritative: AuthoritativeAnswer | None
    if _is_review_report(report):
        authoritative = build_review_authoritative_answer(report)
    else:
        authoritative = build_authoritative_answer(
            executions,
            selected,
            report=report if isinstance(report, dict) else None,
        )

    # Agent-tool success surface (scoped — raw skills never enter normalize).
    out["status"] = "ok"
    out["authoritative_answer_schema_version"] = AUTHORITATIVE_ANSWER_SCHEMA_VERSION
    out.setdefault("selected_agent", selected)
    if tool_name == "agent.default" or "router" in payload:
        out.setdefault("router", payload.get("router", "agent.default"))

    confidence = decision.confidence if decision is not None else 1.0
    reason = (
        decision.reason
        if decision is not None
        else ("direct specialist call" if tool_name != "agent.default" else "routed")
    )
    out["problem_classification"] = ProblemClassification(
        domain=_domain_for_specialist(selected),
        problem_class=_problem_class_from_report(report),
        confidence=confidence,
        reason=reason,
    ).to_dict()
    out["method_summary"] = _method_summary_from(
        specialist=selected,
        report=report if isinstance(report, dict) else {},
        executions=executions,
    ).to_dict()

    if authoritative is not None:
        out["authoritative_answer"] = authoritative.to_dict()
    else:
        out.pop("authoritative_answer", None)

    # Mirror non-authoritative narrative when the specialist already produced one.
    if isinstance(report, dict) and "narrative" in report and "narrative" not in out:
        out["narrative"] = report.get("narrative")

    return out
