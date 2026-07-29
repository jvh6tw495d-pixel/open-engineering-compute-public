"""MCP server: expose OEC specialist agents first, raw skills second.

Thin adapter over :class:`oec.sdk.Engine` plus the repository's `agents/`
companion layer. Default discovery is agent-first: hosts that browse the OEC
catalog should prefer specialist tools unless the caller explicitly asks for a
specific low-level skill id.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

from oec import __version__
from oec.errors import OECError
from oec.sdk import Engine

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

_AGENT_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    _AGENT_DEFAULT_TOOL_NAME: {
        "type": "object",
        "properties": {
            "request": {"type": "string"},
            "preferred_domain": {
                "type": "string",
                "enum": ["optimization", "review", "mathematics", "timeseries", "energy"],
            },
            "ops": {"type": "object"},
            "ops_document": {"type": "object"},
            "execution": {"type": "object"},
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
            "claimed_objective": {"type": "number"},
            "claimed_solver_status": {"type": "string"},
        },
        "additionalProperties": False,
    },
    _AGENT_OPTIMIZATION_TOOL_NAME: {
        "type": "object",
        "properties": {
            "ops": {"type": "object"},
            "demo_label": {"type": "string"},
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
        },
        "additionalProperties": False,
    },
    _AGENT_TIME_SERIES_TOOL_NAME: {
        "type": "object",
        "properties": {
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
        },
        "additionalProperties": False,
    },
    _AGENT_ENERGY_TOOL_NAME: {
        "type": "object",
        "properties": {
            "demo_label": {"type": "string"},
            "skill_id": {"type": "string"},
            "inputs": {"type": "object"},
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


def _infer_domain_from_request(request: str) -> str | None:
    text = request.lower()

    if any(
        token in text
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
        token in text
        for token in ("battery", "energia", "energy", "soc", "three phase", "três fases")
    ):
        return "energy"
    if any(
        token in text
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
        token in text
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
    if any(token in text for token in ("review", "audit", "auditar", "revisar")):
        return "review"
    return None


def _router_target_for(arguments: dict[str, Any]) -> str:
    if "execution" in arguments:
        return _AGENT_REVIEWER_TOOL_NAME
    if "ops" in arguments or "ops_document" in arguments:
        return _AGENT_OPTIMIZATION_TOOL_NAME

    preferred = arguments.get("preferred_domain")
    if preferred == "optimization":
        return _AGENT_OPTIMIZATION_TOOL_NAME
    if preferred == "review":
        return _AGENT_REVIEWER_TOOL_NAME
    if preferred == "mathematics":
        return _AGENT_APPLIED_MATH_TOOL_NAME
    if preferred == "timeseries":
        return _AGENT_TIME_SERIES_TOOL_NAME
    if preferred == "energy":
        return _AGENT_ENERGY_TOOL_NAME

    skill_id = arguments.get("skill_id")
    if isinstance(skill_id, str):
        if skill_id.startswith("optimization."):
            return _AGENT_OPTIMIZATION_TOOL_NAME
        if skill_id.startswith("timeseries."):
            return _AGENT_TIME_SERIES_TOOL_NAME
        if skill_id.startswith(("energy.", "battery.", "electrical.")):
            return _AGENT_ENERGY_TOOL_NAME
        return _AGENT_APPLIED_MATH_TOOL_NAME

    demo_label = str(arguments.get("demo_label", "")).strip().lower()
    if demo_label in {"diet", "diet lp", "min x+y cover", "knapsack", "binary knapsack"}:
        return _AGENT_OPTIMIZATION_TOOL_NAME
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
        return _AGENT_APPLIED_MATH_TOOL_NAME
    if demo_label in {
        "resample",
        "fill_missing",
        "detect_outliers",
        "clip",
        "normalize",
        "rolling",
        "power_to_energy",
    }:
        return _AGENT_TIME_SERIES_TOOL_NAME
    if demo_label in {"balance", "load_metrics", "soc_step", "three_phase"}:
        return _AGENT_ENERGY_TOOL_NAME

    request = arguments.get("request")
    if isinstance(request, str):
        inferred = _infer_domain_from_request(request)
        if inferred == "optimization":
            return _AGENT_OPTIMIZATION_TOOL_NAME
        if inferred == "review":
            return _AGENT_REVIEWER_TOOL_NAME
        if inferred == "timeseries":
            return _AGENT_TIME_SERIES_TOOL_NAME
        if inferred == "energy":
            return _AGENT_ENERGY_TOOL_NAME
        if inferred == "mathematics":
            return _AGENT_APPLIED_MATH_TOOL_NAME

    raise ValueError(
        "agent.default could not infer a specialist. Provide ops/execution, "
        "preferred_domain, demo_label, or explicit skill_id+inputs."
    )


def _run_specialist_by_name(engine: Engine, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    skills_root = _skills_root_for(engine)

    if name == _AGENT_DEFAULT_TOOL_NAME:
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
        raise ValueError(f"{name} requires 'ops' or 'demo_label'")

    if name == _AGENT_REVIEWER_TOOL_NAME:
        from agents.scientific_reviewer.reviewer import ScientificReviewer

        if "execution" not in arguments:
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
    else:
        raise ValueError(f"Unknown agent tool: {name!r}")

    if "demo_label" in arguments:
        return specialist.run_demo(str(arguments["demo_label"])).to_dict()
    if "skill_id" in arguments and "inputs" in arguments:
        return specialist.run_skill(str(arguments["skill_id"]), arguments["inputs"]).to_dict()
    if isinstance(specialist, AppliedMathematicsSpecialist) and "request" in arguments:
        return specialist.run_request(str(arguments["request"])).to_dict()
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
            return _error_result(str(exc), details={"tool": name})
        return CallToolResult(content=[_json_text(payload)], isError=False)

    try:
        engine.registry.get_skill(name)
    except OECError:
        return _error_result(f"Unknown tool: {name!r}", details={"tool": name})

    try:
        result = engine.run(name, arguments)
    except OECError as exc:
        return CallToolResult(content=[_json_text(exc.to_dict())], isError=True)

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
