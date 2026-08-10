"""MCP server: expose OEC specialist agents first, raw skills second.

Thin adapter over :class:`oec.sdk.Engine` plus the repository's `agents/`
companion layer. Default discovery is agent-first: hosts that browse the OEC
catalog should prefer specialist tools unless the caller explicitly asks for a
specific low-level skill id.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import anyio
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

from oec import __version__
from oec.errors import OECError
from oec.mcp.discovery import (
    build_clarification_payload,
    build_skill_suggestion_payload,
    needs_domain_clarification,
    rank_candidate_skills,
    rank_domain_intents,
)
from oec.mcp.divergence import detect_divergence
from oec.mcp.envelope import RouteDecision, confidence_from_score, normalize
from oec.sdk import Engine

_logger = logging.getLogger(__name__)


def _ensure_agents_importable() -> None:
    """Make the repo-root ``agents/`` companion package importable.

    ``agents/`` lives outside ``src/oec`` and has no ``__init__.py`` (a PEP
    420 namespace package), so ``from agents...`` only resolves when the
    repository root is on ``sys.path``. That happens incidentally under
    ``pytest`` (which runs from the repo root) but not for the installed
    ``oec`` console script, whose ``sys.path`` has no reason to include the
    repo root — callers then hit ``ModuleNotFoundError: No module named
    'agents'`` regardless of their own cwd. Resolve the root from this
    file's own location instead of relying on the caller's cwd or an
    externally exported ``PYTHONPATH``.
    """
    # Appended, not inserted at position 0: this should only ever fill in a
    # name that's otherwise unresolved. If some other installed package were
    # ever shadowing "agents", inserting first would silently hide it instead
    # of surfacing a clear conflict.
    repo_root = Path(__file__).resolve().parents[3]
    if (repo_root / "agents").is_dir() and str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))


_ensure_agents_importable()

LIST_AGENTS_TOOL_NAME = "list_agents"
LIST_SKILLS_TOOL_NAME = "list_skills"

_LIST_AGENTS_INPUT_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}
_LIST_SKILLS_INPUT_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}
_LIST_AGENTS_DESCRIPTION = "List built-in OEC specialist agents exposed by this MCP server."
_LIST_SKILLS_DESCRIPTION = (
    "List registered OEC raw skill manifests (mirrors `oec skills list --json`)."
)

_AGENT_DEFAULT_TOOL_NAME = "agent.default"
_AGENT_OPTIMIZATION_TOOL_NAME = "agent.optimization_specialist"
_AGENT_REVIEWER_TOOL_NAME = "agent.scientific_reviewer"
_AGENT_APPLIED_MATH_TOOL_NAME = "agent.applied_mathematics"
_AGENT_TIME_SERIES_TOOL_NAME = "agent.time_series"
_AGENT_ENERGY_TOOL_NAME = "agent.energy"
_AGENT_CONTROL_DYNAMICS_TOOL_NAME = "agent.control_dynamics"
_AGENT_FINANCE_UNCERTAINTY_TOOL_NAME = "agent.finance_uncertainty"
_AGENT_NEURAL_TOOL_NAME = "agent.neural"

# Skill-manifest ``domain`` values each specialist's dispatch spans, for the
# discovery fallback's candidate ranking (agents/*/specialist.py's own
# ``demos`` dicts already mix these per specialist -- e.g. applied math runs
# mathematics.*/linear.*/statistics.*/numerical.* skills).
_DOMAIN_GROUPS: dict[str, tuple[str, ...]] = {
    _AGENT_OPTIMIZATION_TOOL_NAME: ("optimization",),
    _AGENT_APPLIED_MATH_TOOL_NAME: ("mathematics", "linear", "statistics", "numerical"),
    _AGENT_TIME_SERIES_TOOL_NAME: ("timeseries",),
    # Chemistry / multiphysics / foundation physics skills are surfaced via the
    # Energy specialist until dedicated specialists exist (3.3.1 recovery).
    _AGENT_ENERGY_TOOL_NAME: (
        "energy",
        "battery",
        "electrical",
        "chemistry",
        "multiphysics",
        "thermal",
        "mechanics",
        "fluids",
        "materials",
    ),
    _AGENT_CONTROL_DYNAMICS_TOOL_NAME: ("control", "dynamics"),
    _AGENT_FINANCE_UNCERTAINTY_TOOL_NAME: ("finance", "uncertainty"),
    # ADR 0031 / 0033 — dense neural families + evolutionary + hybrid training.
    _AGENT_NEURAL_TOOL_NAME: ("neural", "evolutionary"),
}

# Wave 2 (v2.5.3): a host may voluntarily attach its own belief about the
# answer alongside the call. Deliberately unconstrained (no "type") — a claim
# is compared structurally against ``authoritative_answer.values`` post
# serialization (see ``oec.mcp.divergence``), so it can be any JSON shape.
# This is the *only* channel for host claims; no new MCP tool is introduced.
_CLAIMED_ANSWER_SCHEMA: dict[str, Any] = {}

_AGENT_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    _AGENT_DEFAULT_TOOL_NAME: {
        "type": "object",
        "properties": {
            "request": {"type": "string"},
            "preferred_domain": {
                "type": "string",
                "enum": [
                    "optimization",
                    "review",
                    "mathematics",
                    "timeseries",
                    "energy",
                    "control_dynamics",
                    "finance_uncertainty",
                    "neural",
                ],
            },
            "ops": {"type": "object"},
            "ops_document": {"type": "object"},
            "execution": {"type": "object"},
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
            "claimed_objective": {"type": "number"},
            "claimed_solver_status": {"type": "string"},
            "claimed_answer": _CLAIMED_ANSWER_SCHEMA,
        },
        "additionalProperties": False,
    },
    _AGENT_OPTIMIZATION_TOOL_NAME: {
        "type": "object",
        "properties": {
            "ops": {"type": "object"},
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
            "claimed_answer": _CLAIMED_ANSWER_SCHEMA,
        },
        "additionalProperties": False,
    },
    _AGENT_REVIEWER_TOOL_NAME: {
        "type": "object",
        "properties": {
            "ops_document": {"type": "object"},
            "execution": {"type": "object"},
            "claimed_objective": {"type": "number"},
            "claimed_solver_status": {"type": "string"},
            "claimed_answer": _CLAIMED_ANSWER_SCHEMA,
        },
        "required": ["execution"],
        "additionalProperties": False,
    },
    _AGENT_APPLIED_MATH_TOOL_NAME: {
        "type": "object",
        "properties": {
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
            "claimed_answer": _CLAIMED_ANSWER_SCHEMA,
        },
        "additionalProperties": False,
    },
    _AGENT_TIME_SERIES_TOOL_NAME: {
        "type": "object",
        "properties": {
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
            "claimed_answer": _CLAIMED_ANSWER_SCHEMA,
        },
        "additionalProperties": False,
    },
    _AGENT_ENERGY_TOOL_NAME: {
        "type": "object",
        "properties": {
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
            "claimed_answer": _CLAIMED_ANSWER_SCHEMA,
        },
        "additionalProperties": False,
    },
    _AGENT_CONTROL_DYNAMICS_TOOL_NAME: {
        "type": "object",
        "properties": {
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
            "claimed_answer": _CLAIMED_ANSWER_SCHEMA,
        },
        "additionalProperties": False,
    },
    _AGENT_FINANCE_UNCERTAINTY_TOOL_NAME: {
        "type": "object",
        "properties": {
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
            "claimed_answer": _CLAIMED_ANSWER_SCHEMA,
        },
        "additionalProperties": False,
    },
    _AGENT_NEURAL_TOOL_NAME: {
        "type": "object",
        "properties": {
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
            "claimed_answer": _CLAIMED_ANSWER_SCHEMA,
        },
        "additionalProperties": False,
    },
}

_AGENT_TOOL_DESCRIPTIONS: dict[str, str] = {
    _AGENT_DEFAULT_TOOL_NAME: (
        "Default OEC router. Use this for generic requests so OEC chooses the right "
        "specialist agent. Only bypass it when the caller explicitly wants a specific raw skill."
    ),
    _AGENT_OPTIMIZATION_TOOL_NAME: (
        "Optimization Specialist: default LP/MILP path. Accepts a full OPS document "
        "or a deterministic demo_label."
    ),
    _AGENT_REVIEWER_TOOL_NAME: (
        "Scientific Reviewer: independent audit of OPS + ExecutionResult without re-solving."
    ),
    _AGENT_APPLIED_MATH_TOOL_NAME: (
        "Applied Mathematics Specialist: domain wrapper over mathematics/linear/"
        "statistics/numerical skills."
    ),
    _AGENT_TIME_SERIES_TOOL_NAME: (
        "Time-Series Specialist: domain wrapper over timeseries.* quality/grid skills."
    ),
    _AGENT_ENERGY_TOOL_NAME: (
        "Energy Specialist: domain wrapper over public energy/battery/electrical skills."
    ),
    _AGENT_CONTROL_DYNAMICS_TOOL_NAME: (
        "Control & Dynamics Specialist: control.* and dynamics.* skills."
    ),
    _AGENT_FINANCE_UNCERTAINTY_TOOL_NAME: (
        "Finance & Uncertainty Specialist: finance.* and uncertainty.* skills."
    ),
    _AGENT_NEURAL_TOOL_NAME: (
        "Neural & Evolutionary Specialist: neural.* training/families/search and "
        "evolutionary.* single/multi-objective skills (ADR 0031 / ADR 0033). "
        "Requires oec[neural] / oec[evolutionary] extras for most demos."
    ),
}


def _raw_skill_description(base_description: str) -> str:
    return (
        f"{base_description} "
        "[Low-level OEC function. Prefer `agent.default` unless the caller explicitly "
        "asks for this specific raw function.]"
    )


def _json_text(payload: Any) -> TextContent:
    """Serialize ``payload`` as a single MCP text content block."""
    return TextContent(type="text", text=json.dumps(payload, default=str))


def _error_result(message: str, *, details: dict[str, Any] | None = None) -> CallToolResult:
    """Build a failed tool result without raising (keeps the MCP session alive)."""
    body: dict[str, Any] = {"error": message}
    if details is not None:
        body["details"] = details
    return CallToolResult(content=[_json_text(body)], isError=True)


def _agent_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": _AGENT_DEFAULT_TOOL_NAME,
            "title": "OEC Default Router",
            "kind": "agent_router",
            "domain": "router",
            "default": True,
            "description": _AGENT_TOOL_DESCRIPTIONS[_AGENT_DEFAULT_TOOL_NAME],
        },
        {
            "id": _AGENT_OPTIMIZATION_TOOL_NAME,
            "title": "Optimization Specialist",
            "kind": "agent",
            "domain": "optimization",
            "default": True,
            "description": _AGENT_TOOL_DESCRIPTIONS[_AGENT_OPTIMIZATION_TOOL_NAME],
        },
        {
            "id": _AGENT_REVIEWER_TOOL_NAME,
            "title": "Scientific Reviewer",
            "kind": "agent",
            "domain": "review",
            "default": True,
            "description": _AGENT_TOOL_DESCRIPTIONS[_AGENT_REVIEWER_TOOL_NAME],
        },
        {
            "id": _AGENT_APPLIED_MATH_TOOL_NAME,
            "title": "Applied Mathematics Specialist",
            "kind": "agent",
            "domain": "mathematics",
            "default": True,
            "description": _AGENT_TOOL_DESCRIPTIONS[_AGENT_APPLIED_MATH_TOOL_NAME],
        },
        {
            "id": _AGENT_TIME_SERIES_TOOL_NAME,
            "title": "Time-Series Specialist",
            "kind": "agent",
            "domain": "timeseries",
            "default": True,
            "description": _AGENT_TOOL_DESCRIPTIONS[_AGENT_TIME_SERIES_TOOL_NAME],
        },
        {
            "id": _AGENT_ENERGY_TOOL_NAME,
            "title": "Energy Specialist",
            "kind": "agent",
            "domain": "energy",
            "default": True,
            "description": _AGENT_TOOL_DESCRIPTIONS[_AGENT_ENERGY_TOOL_NAME],
        },
        {
            "id": _AGENT_CONTROL_DYNAMICS_TOOL_NAME,
            "title": "Control & Dynamics Specialist",
            "kind": "agent",
            "domain": "control_dynamics",
            "default": True,
            "description": _AGENT_TOOL_DESCRIPTIONS[_AGENT_CONTROL_DYNAMICS_TOOL_NAME],
        },
        {
            "id": _AGENT_FINANCE_UNCERTAINTY_TOOL_NAME,
            "title": "Finance & Uncertainty Specialist",
            "kind": "agent",
            "domain": "finance_uncertainty",
            "default": True,
            "description": _AGENT_TOOL_DESCRIPTIONS[_AGENT_FINANCE_UNCERTAINTY_TOOL_NAME],
        },
        {
            "id": _AGENT_NEURAL_TOOL_NAME,
            "title": "Neural & Evolutionary Specialist",
            "kind": "agent",
            "domain": "neural",
            "default": True,
            "description": _AGENT_TOOL_DESCRIPTIONS[_AGENT_NEURAL_TOOL_NAME],
        },
    ]


def _build_agent_tools() -> list[Tool]:
    return [
        Tool(
            name=str(entry["id"]),
            description=str(entry["description"]),
            inputSchema=_AGENT_TOOL_SCHEMAS[str(entry["id"])],
        )
        for entry in _agent_catalog()
    ]


def _skills_root_for(engine: Engine) -> Path:
    return getattr(engine, "skills_root", Path("skills"))


def _contains_token(text: str, token: str) -> bool:
    """Match ``token`` at a word boundary, not merely as a bare substring.

    Only the leading boundary is required (no trailing ``\\b``) so
    deliberate multi-lingual stems like ``"restri"`` (restrição,
    restringir, restrict...) or ``"autocorrelat"`` (autocorrelation,
    autocorrelação) still match anywhere inside a longer word. What this
    fixes: bare ``"lp" in text`` matched inside "he**lp**" and ``"ops" in
    text`` matched inside "sh**ops**"/"dr**ops**", silently misrouting
    ordinary requests to the optimization domain.
    """
    pattern = r"\b" + re.escape(token)
    if len(token) <= 3:
        pattern += r"\b"
    return re.search(pattern, text) is not None


def _infer_domain_from_request(request: str) -> str | None:
    text = request.lower()

    if any(
        _contains_token(text, token)
        for token in (
            "deriv",
            "integral",
            "raiz",
            "root",
            "equa",
            "maximize",
            "maximizar",
            "minimum",
            "minimo",
            "mínimo",
            "máximo",
            "maximum",
            "função",
            "funcao",
            "function",
            "velocidade",
            "velocidade média",
            "mais rápido",
            "mais lento",
            "faster",
            "slower",
        )
    ):
        return "mathematics"
    if any(
        _contains_token(text, token)
        for token in (
            "battery",
            "energia",
            "energy",
            "soc",
            "three phase",
            "três fases",
            "chemistry",
            "química",
            "nernst",
            "arrhenius",
            "stoichiometry",
            "multiphysics",
            "multifísica",
            "coupling",
            "acoplamento",
            "thermal",
            "térmico",
            "bernoulli",
            "thd",
            "harmonic",
        )
    ):
        return "energy"
    if any(
        _contains_token(text, token)
        for token in (
            "series",
            "time series",
            "série temporal",
            "resample",
            "rolling",
            "autocorrelat",
            "autocorrelação",
            "pacf",
            "autocorrelação parcial",
            "partial autocorrelation",
            "yule-walker",
            "yule walker",
            "levinson",
            "durbin",
            "autoregress",
            "autorregress",
        )
    ):
        return "timeseries"
    if any(
        _contains_token(text, token)
        for token in (
            "lp",
            "milp",
            "ops",
            "objective",
            "constraint",
            "restri",
            "otimização linear",
            "optimization",
        )
    ):
        return "optimization"
    if any(_contains_token(text, token) for token in ("review", "audit", "auditar", "revisar")):
        return "review"
    if any(
        _contains_token(text, token)
        for token in ("pid", "kalman", "stability", "estabilidade", "state space")
    ):
        return "control_dynamics"
    if any(
        _contains_token(text, token)
        for token in ("finance", "finanças", "var", "uncertainty", "incerteza", "morris")
    ):
        return "finance_uncertainty"
    if any(
        _contains_token(text, token)
        for token in (
            "neural",
            "neuronal",
            "mlp",
            "pytorch",
            "torch",
            "lstm",
            "cnn",
            "transformer",
            "neuroevolution",
            "evolutionary",
            "evolutivo",
            "genetic algorithm",
            "algoritmo genético",
            "nsga",
            "cma-es",
            "cmaes",
            "particle swarm",
            "enxame de partículas",
        )
    ):
        return "neural"
    return None


_EXECUTION_RESULT_REQUIRED_KEYS = ("status", "skill", "method", "started_at")


def _has_execution_payload(arguments: dict[str, Any]) -> bool:
    """True only if ``arguments["execution"]`` looks like a real ExecutionResult.

    Local LLMs sometimes hallucinate an empty/placeholder ``execution: {}``
    alongside an otherwise clear optimization/other-domain request. Routing
    on bare key presence sent that straight to agent.scientific_reviewer,
    which then failed with a validation error even though ``ops``,
    ``preferred_domain``, or the request text pointed at a different,
    perfectly runnable specialist.
    """
    execution = arguments.get("execution")
    if not isinstance(execution, dict):
        return False
    return all(key in execution for key in _EXECUTION_RESULT_REQUIRED_KEYS)


def _route_decision(arguments: dict[str, Any]) -> RouteDecision:
    """Resolve the specialist target plus confidence / reason / signal.

    Confidence for free-text domain ranking is derived from
    :func:`rank_domain_intents` scores (mapped onto ``[0, 1]``). Explicit
    machine-readable signals (ops, preferred_domain, skill_id, demo_label,
    real execution) are treated as full-confidence decisions.
    """
    if _has_execution_payload(arguments):
        return RouteDecision(
            target=_AGENT_REVIEWER_TOOL_NAME,
            confidence=1.0,
            reason="execution payload present",
            signal="execution",
        )
    if "ops" in arguments or "ops_document" in arguments:
        return RouteDecision(
            target=_AGENT_OPTIMIZATION_TOOL_NAME,
            confidence=1.0,
            reason="ops document present",
            signal="ops",
        )

    preferred = arguments.get("preferred_domain")
    preferred_targets = {
        "optimization": _AGENT_OPTIMIZATION_TOOL_NAME,
        "review": _AGENT_REVIEWER_TOOL_NAME,
        "mathematics": _AGENT_APPLIED_MATH_TOOL_NAME,
        "timeseries": _AGENT_TIME_SERIES_TOOL_NAME,
        "energy": _AGENT_ENERGY_TOOL_NAME,
        "control_dynamics": _AGENT_CONTROL_DYNAMICS_TOOL_NAME,
        "finance_uncertainty": _AGENT_FINANCE_UNCERTAINTY_TOOL_NAME,
        "neural": _AGENT_NEURAL_TOOL_NAME,
    }
    if preferred in preferred_targets:
        return RouteDecision(
            target=preferred_targets[preferred],
            confidence=1.0,
            reason=f"preferred_domain={preferred}",
            signal="preferred_domain",
        )

    skill_id = arguments.get("skill_id")
    if isinstance(skill_id, str):
        if skill_id.startswith("optimization."):
            target = _AGENT_OPTIMIZATION_TOOL_NAME
        elif skill_id.startswith("timeseries."):
            target = _AGENT_TIME_SERIES_TOOL_NAME
        elif skill_id.startswith(("energy.", "battery.", "electrical.")):
            target = _AGENT_ENERGY_TOOL_NAME
        elif skill_id.startswith(("control.", "dynamics.")):
            target = _AGENT_CONTROL_DYNAMICS_TOOL_NAME
        elif skill_id.startswith(("finance.", "uncertainty.")):
            target = _AGENT_FINANCE_UNCERTAINTY_TOOL_NAME
        elif skill_id.startswith(("neural.", "evolutionary.")):
            target = _AGENT_NEURAL_TOOL_NAME
        else:
            target = _AGENT_APPLIED_MATH_TOOL_NAME
        return RouteDecision(
            target=target,
            confidence=1.0,
            reason=f"skill_id prefix for {skill_id}",
            signal="skill_id",
        )

    demo_label = str(arguments.get("demo_label", "")).strip().lower()
    if demo_label in {"diet", "diet lp", "min x+y cover", "knapsack", "binary knapsack"}:
        return RouteDecision(
            target=_AGENT_OPTIMIZATION_TOOL_NAME,
            confidence=1.0,
            reason=f"demo_label={demo_label}",
            signal="demo_label",
        )
    if demo_label in {
        "sqrt2",
        "solve_root",
        "integrate_x2",
        "linear_identity",
        "matrix_properties",
        "describe",
        "monte_carlo",
        "ode_decay",
    }:
        return RouteDecision(
            target=_AGENT_APPLIED_MATH_TOOL_NAME,
            confidence=1.0,
            reason=f"demo_label={demo_label}",
            signal="demo_label",
        )
    if demo_label in {
        "resample",
        "fill_missing",
        "detect_outliers",
        "clip",
        "normalize",
        "rolling",
        "power_to_energy",
    }:
        return RouteDecision(
            target=_AGENT_TIME_SERIES_TOOL_NAME,
            confidence=1.0,
            reason=f"demo_label={demo_label}",
            signal="demo_label",
        )
    if demo_label in {
        "balance",
        "load_metrics",
        "soc_step",
        "three_phase",
        "dc_power_flow",
    }:
        return RouteDecision(
            target=_AGENT_ENERGY_TOOL_NAME,
            confidence=1.0,
            reason=f"demo_label={demo_label}",
            signal="demo_label",
        )
    if demo_label in {"pid", "kalman", "stability"}:
        return RouteDecision(
            target=_AGENT_CONTROL_DYNAMICS_TOOL_NAME,
            confidence=1.0,
            reason=f"demo_label={demo_label}",
            signal="demo_label",
        )
    if demo_label in {"returns", "var", "propagate"}:
        return RouteDecision(
            target=_AGENT_FINANCE_UNCERTAINTY_TOOL_NAME,
            confidence=1.0,
            reason=f"demo_label={demo_label}",
            signal="demo_label",
        )
    if demo_label in {
        "mlp_regressor",
        "mlp_classifier",
        "optimize_single",
        "nsga2",
        "training_supervised",
        "de",
    }:
        return RouteDecision(
            target=_AGENT_NEURAL_TOOL_NAME,
            confidence=1.0,
            reason=f"demo_label={demo_label}",
            signal="demo_label",
        )

    request = arguments.get("request")
    if isinstance(request, str):
        intent_targets = {
            "optimization": _AGENT_OPTIMIZATION_TOOL_NAME,
            "review": _AGENT_REVIEWER_TOOL_NAME,
            "timeseries": _AGENT_TIME_SERIES_TOOL_NAME,
            "energy": _AGENT_ENERGY_TOOL_NAME,
            "mathematics": _AGENT_APPLIED_MATH_TOOL_NAME,
            "control_dynamics": _AGENT_CONTROL_DYNAMICS_TOOL_NAME,
            "finance_uncertainty": _AGENT_FINANCE_UNCERTAINTY_TOOL_NAME,
            "neural": _AGENT_NEURAL_TOOL_NAME,
        }
        intents = rank_domain_intents(request)
        if intents and not needs_domain_clarification(intents):
            top = intents[0]
            matched = ", ".join(top.matched_terms) if top.matched_terms else top.domain
            return RouteDecision(
                target=intent_targets[top.domain],
                confidence=confidence_from_score(top.score),
                reason=f"matched: {matched}",
                signal="request_intent",
            )
        inferred = _infer_domain_from_request(request)
        if inferred in intent_targets:
            return RouteDecision(
                target=intent_targets[inferred],
                confidence=0.5,
                reason=f"inferred domain={inferred}",
                signal="request_inferred",
            )

    raise ValueError(
        "agent.default could not infer a specialist. Provide ops/execution, "
        "preferred_domain, demo_label, or explicit skill_id+inputs."
    )


def _router_target_for(arguments: dict[str, Any]) -> str:
    """Thin wrapper kept for existing callers/tests; delegates to :func:`_route_decision`."""
    return _route_decision(arguments).target


def _run_specialist_by_name(engine: Engine, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    skills_root = _skills_root_for(engine)

    if name == _AGENT_DEFAULT_TOOL_NAME:
        request = arguments.get("request")
        # Only the free-text branch may clarify. Explicit machine-readable
        # signals retain their existing precedence in _router_target_for.
        explicit = any(
            key in arguments
            for key in (
                "execution",
                "ops",
                "ops_document",
                "preferred_domain",
                "skill_id",
                "demo_label",
            )
        )
        if isinstance(request, str) and not explicit:
            intents = rank_domain_intents(request)
            if needs_domain_clarification(intents):
                payload = build_clarification_payload(request, intents)
                payload["router"] = _AGENT_DEFAULT_TOOL_NAME
                payload["reason"] = "intent_absent" if not intents else "intent_tied"
                return payload
        target = _router_target_for(arguments)
        routed_payload = dict(arguments)
        routed_payload.pop("preferred_domain", None)
        specialist_result = _run_specialist_by_name(engine, target, routed_payload)
        return {
            "router": _AGENT_DEFAULT_TOOL_NAME,
            "selected_agent": target,
            "request": arguments.get("request"),
            "result": specialist_result,
        }

    if name == _AGENT_OPTIMIZATION_TOOL_NAME:
        from agents.optimization_specialist.specialist import OptimizationSpecialist

        opt_specialist = OptimizationSpecialist(skills_root=skills_root)
        if "ops" in arguments:
            return opt_specialist.execute_ops(arguments["ops"]).to_dict()
        if "demo_label" in arguments:
            return opt_specialist.run_demo(str(arguments["demo_label"])).to_dict()
        if "skill_id" in arguments and "inputs" in arguments:
            return opt_specialist.run_skill(
                str(arguments["skill_id"]), arguments["inputs"]
            ).to_dict()
        if "request" in arguments:
            request_text = str(arguments["request"])
            return build_skill_suggestion_payload(
                name,
                request_text,
                rank_candidate_skills(engine, request_text, domains=_DOMAIN_GROUPS[name]),
            )
        raise ValueError(f"{name} requires 'ops', 'demo_label', or both 'skill_id' and 'inputs'")

    if name == _AGENT_REVIEWER_TOOL_NAME:
        from agents.scientific_reviewer.reviewer import ScientificReviewer

        if "execution" not in arguments:
            if "request" in arguments:
                return build_skill_suggestion_payload(
                    name,
                    str(arguments["request"]),
                    candidates=[],
                    hint=(
                        "agent.scientific_reviewer audits a prior ExecutionResult; it "
                        "does not run skills or accept free text itself. Run an "
                        "optimization/applied_mathematics/time_series/energy agent "
                        "first, then call this agent again with that result's "
                        "'execution' (and optionally 'ops_document')."
                    ),
                )
            raise ValueError(f"{name} requires 'execution'")
        reviewer = ScientificReviewer()
        return reviewer.review(
            arguments.get("ops_document"),
            arguments["execution"],
            claimed_objective=arguments.get("claimed_objective"),
            claimed_solver_status=arguments.get("claimed_solver_status"),
        ).to_dict()

    from agents.applied_mathematics.specialist import AppliedMathematicsSpecialist
    from agents.common import SkillSpecialist

    specialist: SkillSpecialist
    if name == _AGENT_APPLIED_MATH_TOOL_NAME:
        specialist = AppliedMathematicsSpecialist(skills_root=skills_root)
    elif name == _AGENT_TIME_SERIES_TOOL_NAME:
        from agents.time_series.specialist import TimeSeriesSpecialist

        specialist = TimeSeriesSpecialist(skills_root=skills_root)
    elif name == _AGENT_ENERGY_TOOL_NAME:
        from agents.energy.specialist import EnergySpecialist

        specialist = EnergySpecialist(skills_root=skills_root)
    elif name == _AGENT_CONTROL_DYNAMICS_TOOL_NAME:
        from agents.control_dynamics.specialist import ControlDynamicsSpecialist

        specialist = ControlDynamicsSpecialist(skills_root=skills_root)
    elif name == _AGENT_FINANCE_UNCERTAINTY_TOOL_NAME:
        from agents.finance_uncertainty.specialist import FinanceUncertaintySpecialist

        specialist = FinanceUncertaintySpecialist(skills_root=skills_root)
    elif name == _AGENT_NEURAL_TOOL_NAME:
        from agents.neural.specialist import NeuralEvolutionarySpecialist

        specialist = NeuralEvolutionarySpecialist(skills_root=skills_root)
    else:
        raise ValueError(f"Unknown agent tool: {name!r}")

    if "demo_label" in arguments:
        return specialist.run_demo(str(arguments["demo_label"])).to_dict()
    if "skill_id" in arguments and "inputs" in arguments:
        return specialist.run_skill(str(arguments["skill_id"]), arguments["inputs"]).to_dict()
    if "request" in arguments:
        request_text = str(arguments["request"])
        if isinstance(specialist, AppliedMathematicsSpecialist):
            try:
                return specialist.run_request(request_text).to_dict()
            except ValueError:
                pass  # narrow scalar-extrema grammar didn't match -- fall through
        return build_skill_suggestion_payload(
            name,
            request_text,
            rank_candidate_skills(engine, request_text, domains=_DOMAIN_GROUPS[name]),
        )
    raise ValueError(f"{name} requires 'demo_label' or both 'skill_id' and 'inputs'")


def build_tools(engine: Engine) -> list[Tool]:
    """Agent-first MCP catalog: specialists, discovery tools, then raw skills.

    Raw skill tools keep each skill's original ``input.schema.json``. The MCP
    surface intentionally exposes specialist agents first so hosts prefer them
    by default unless the caller explicitly names a low-level skill id.
    """
    tools: list[Tool] = _build_agent_tools()
    tools.append(
        Tool(
            name=LIST_AGENTS_TOOL_NAME,
            description=_LIST_AGENTS_DESCRIPTION,
            inputSchema=dict(_LIST_AGENTS_INPUT_SCHEMA),
        )
    )
    tools.append(
        Tool(
            name=LIST_SKILLS_TOOL_NAME,
            description=_LIST_SKILLS_DESCRIPTION,
            inputSchema=dict(_LIST_SKILLS_INPUT_SCHEMA),
        )
    )
    for manifest in engine.registry.list_skills(include_retired=False):
        skill = engine.registry.get_skill(manifest.id, manifest.version)
        description = _raw_skill_description(skill.manifest.description or skill.manifest.title)
        tools.append(
            Tool(
                name=skill.manifest.id,
                description=description,
                inputSchema=skill.input_schema,
            )
        )
    return tools


def call_tool(engine: Engine, name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Dispatch a tool call against ``engine``.

    Sync on purpose: :meth:`Engine.run` already serializes executions
    (ADR 0015); the MCP handler just waits if another call is in progress.
    """
    if name == LIST_AGENTS_TOOL_NAME:
        return CallToolResult(content=[_json_text(_agent_catalog())], isError=False)

    if name == LIST_SKILLS_TOOL_NAME:
        manifests = engine.registry.list_skills(include_retired=False)
        manifest_payload = [m.model_dump(mode="json", by_alias=True) for m in manifests]
        return CallToolResult(content=[_json_text(manifest_payload)], isError=False)

    if not isinstance(arguments, dict):
        return _error_result(
            f"'arguments' must be an object, got {type(arguments).__name__}",
            details={"tool": name},
        )

    if name in _AGENT_TOOL_SCHEMAS:
        try:
            payload = _run_specialist_by_name(engine, name, arguments)
        except (OECError, ValueError, TypeError) as exc:
            return _error_result(str(exc), details={"tool": name, "error_type": type(exc).__name__})
        except Exception as exc:  # e.g. a specialist's lazy import failing
            _logger.exception("unexpected error dispatching agent tool %r", name)
            return _error_result(
                f"{type(exc).__name__}: {exc}",
                details={"tool": name, "error_type": type(exc).__name__},
            )
        # Wrap once at the call_tool boundary (never inside _run_specialist_by_name —
        # agent.default recurses and would double-wrap). Raw-skill dispatch is
        # intentionally left untouched so ExecutionStatus semantics stay intact.
        decision: RouteDecision | None = None
        if name == _AGENT_DEFAULT_TOOL_NAME:
            if payload.get("status") not in (
                "needs_clarification",
                "needs_more_information",
            ):
                try:
                    decision = _route_decision(arguments)
                except ValueError:
                    decision = None
        else:
            decision = RouteDecision(
                target=name,
                confidence=1.0,
                reason="direct specialist call",
                signal="direct",
            )
        payload = normalize(payload, tool_name=name, decision=decision)

        # Wave 2: a host may voluntarily attach ``claimed_answer``. OEC never
        # trusts or substitutes it -- authoritative_answer above is already
        # final -- this only ever *adds* an advisory warning key when the
        # claim disagrees with what OEC just computed (fail-closed, additive).
        # Scoped to the agent-tool success surface (``status: "ok"``): the
        # needs_clarification/needs_more_information passthrough shapes never
        # mint authority by design, so a leftover claim there is not "host
        # corruption" -- there was nothing to compute yet.
        if payload.get("status") == "ok":
            divergence = detect_divergence(
                payload.get("authoritative_answer"), arguments.get("claimed_answer")
            )
            if divergence is not None:
                payload["host_output_diverged"] = divergence

        return CallToolResult(content=[_json_text(payload)], isError=False)

    try:
        engine.registry.get_skill(name)
    except OECError:
        return _error_result(f"Unknown tool: {name!r}", details={"tool": name})

    try:
        result = engine.run(name, arguments)
    except OECError as exc:
        return CallToolResult(content=[_json_text(exc.to_dict())], isError=True)
    except Exception as exc:
        _logger.exception("unexpected error running skill %r", name)
        return _error_result(
            f"{type(exc).__name__}: {exc}",
            details={"tool": name, "error_type": type(exc).__name__},
        )

    return CallToolResult(
        content=[_json_text(result.model_dump(mode="json"))],
        isError=False,
    )


def build_server(engine: Engine) -> Server[Any, Any]:
    """Wire ``engine`` into a low-level MCP :class:`~mcp.server.lowlevel.Server`.

    Uses the low-level API (not FastMCP) so each raw skill's pre-built JSON
    Schema dict can be passed as ``inputSchema`` verbatim.
    """
    server: Server[Any, Any] = Server("oec", version=__version__)

    @server.list_tools()  # type: ignore
    async def list_tools() -> list[Tool]:
        return build_tools(engine)

    @server.call_tool(validate_input=False)  # type: ignore
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        return call_tool(engine, name, arguments or {})

    return server


def run_stdio_server(skills_root: str | Path = "skills") -> None:
    """Build a warmed :class:`~oec.sdk.Engine` and serve agents + skills over stdio."""
    engine = Engine(skills_root=skills_root)
    engine.warm()
    server = build_server(engine)

    async def _serve() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    anyio.run(_serve)
