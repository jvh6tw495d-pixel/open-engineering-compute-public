"""Integration tests for the OEC MCP server (ADR 0015).

Exercises the real ``skills/`` directory through the same ``oec.sdk.Engine``
facade the CLI and REST API use — handler logic is tested directly (no stdio
transport) so failures point at dispatch/serialization rather than MCP framing.
"""

from __future__ import annotations

import json
import math
from typing import Any

import anyio
import pytest
from mcp import types as mcp_types

from oec.mcp.server import (
    LIST_AGENTS_TOOL_NAME,
    LIST_SKILLS_TOOL_NAME,
    _router_target_for,
    _run_specialist_by_name,
    build_server,
    build_tools,
    call_tool,
    run_stdio_server,
)
from oec.sdk import Engine


@pytest.fixture(scope="module")
def engine() -> Engine:
    eng = Engine(skills_root="skills")
    eng.warm()
    return eng


def _parse_content(result: Any) -> Any:
    assert result.content, "tool result has no content blocks"
    assert result.content[0].type == "text"
    return json.loads(result.content[0].text)


def test_list_tools_includes_agents_skills_and_discovery(engine: Engine) -> None:
    tools = build_tools(engine)
    by_name = {tool.name: tool for tool in tools}

    assert LIST_AGENTS_TOOL_NAME in by_name
    assert LIST_SKILLS_TOOL_NAME in by_name
    assert by_name[LIST_AGENTS_TOOL_NAME].inputSchema == {
        "type": "object",
        "properties": {},
    }
    assert by_name[LIST_SKILLS_TOOL_NAME].inputSchema == {
        "type": "object",
        "properties": {},
    }
    assert tools[0].name == "agent.default"

    skill_ids = {m.id for m in engine.registry.list_skills(include_retired=False)}
    assert "mathematics.solve_root" in skill_ids
    for skill_id in skill_ids:
        assert skill_id in by_name

    # inputSchema is the skill's real schema, not a hand-written copy.
    loaded = engine.registry.get_skill("mathematics.solve_root")
    assert by_name["mathematics.solve_root"].inputSchema == loaded.input_schema
    assert "Prefer `agent.default`" in by_name["mathematics.solve_root"].description

    # Agent-first catalog: fixed agent tools + discovery + raw skills.
    assert len(tools) == len(skill_ids) + 8


def test_call_tool_solve_root_returns_validated_result(engine: Engine) -> None:
    result = call_tool(
        engine,
        "mathematics.solve_root",
        {"expression": "x**2 - 2", "bracket": [0, 2]},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["status"] == "VALIDATED"
    assert math.isclose(payload["result"]["root"], math.sqrt(2), rel_tol=1e-9)


def test_call_tool_list_skills_returns_catalog(engine: Engine) -> None:
    result = call_tool(engine, LIST_SKILLS_TOOL_NAME, {})
    assert result.isError is False
    catalog = _parse_content(result)
    assert isinstance(catalog, list)
    assert len(catalog) >= 6
    ids = {entry["id"] for entry in catalog}
    assert "mathematics.solve_root" in ids
    # Mirrors oec skills list --json shape (manifest dump with aliases).
    sample = next(entry for entry in catalog if entry["id"] == "mathematics.solve_root")
    assert "version" in sample
    assert "title" in sample
    assert "domain" in sample


def test_call_tool_list_agents_returns_catalog(engine: Engine) -> None:
    result = call_tool(engine, LIST_AGENTS_TOOL_NAME, {})
    assert result.isError is False
    catalog = _parse_content(result)
    assert isinstance(catalog, list)
    ids = {entry["id"] for entry in catalog}
    assert "agent.default" in ids
    sample = next(entry for entry in catalog if entry["id"] == "agent.default")
    assert sample["kind"] == "agent_router"
    assert sample["default"] is True


def test_call_tool_default_router_runs_optimization_agent(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {"request": "solve optimization problem", "demo_label": "diet"},
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["router"] == "agent.default"
    assert payload["selected_agent"] == "agent.optimization_specialist"
    assert payload["result"]["skill_id"] == "optimization.lp"
    assert payload["result"]["execution"]["status"] == "VALIDATED"


def test_call_tool_optimization_agent_runs_demo(engine: Engine) -> None:
    result = call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["problem_class"] == "lp"
    assert payload["skill_id"] == "optimization.lp"
    assert payload["execution"]["status"] == "VALIDATED"


def test_call_tool_scientific_reviewer_reviews_agent_output(engine: Engine) -> None:
    solve = _parse_content(
        call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    )
    result = call_tool(
        engine,
        "agent.scientific_reviewer",
        {
            "ops_document": solve["ops"],
            "execution": solve["execution"],
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["passed"] is True


def test_call_tool_domain_agent_runs_explicit_skill(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.applied_mathematics",
        {
            "skill_id": "mathematics.solve_root",
            "inputs": {"expression": "x**2 - 2", "bracket": [0, 2]},
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["agent"] == "applied_mathematics_specialist"
    assert payload["skill_id"] == "mathematics.solve_root"
    assert payload["execution"]["status"] == "VALIDATED"


def test_call_tool_default_router_respects_explicit_skill(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "call specific function",
            "skill_id": "mathematics.solve_root",
            "inputs": {"expression": "x**2 - 2", "bracket": [0, 2]},
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.applied_mathematics"
    assert payload["result"]["skill_id"] == "mathematics.solve_root"
    assert payload["result"]["execution"]["status"] == "VALIDATED"


def test_call_tool_optimization_agent_runs_full_ops(engine: Engine) -> None:
    ops = {
        "ops_version": "0.1.0",
        "problem_class": "lp",
        "sense": "min",
        "variables": [
            {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
            {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
        ],
        "constraints": [{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
        "objective": {"coeffs": {"x": 1, "y": 1}},
    }
    result = call_tool(engine, "agent.optimization_specialist", {"ops": ops})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["skill_id"] == "optimization.lp"
    assert payload["execution"]["status"] == "VALIDATED"


def test_call_tool_optimization_agent_requires_ops_or_demo(engine: Engine) -> None:
    result = call_tool(engine, "agent.optimization_specialist", {})
    assert result.isError is True
    payload = _parse_content(result)
    assert "requires 'ops' or 'demo_label'" in payload["error"]


def test_call_tool_scientific_reviewer_requires_execution(engine: Engine) -> None:
    result = call_tool(engine, "agent.scientific_reviewer", {})
    assert result.isError is True
    payload = _parse_content(result)
    assert "requires 'execution'" in payload["error"]


def test_call_tool_time_series_agent_runs_demo(engine: Engine) -> None:
    result = call_tool(engine, "agent.time_series", {"demo_label": "resample"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["agent"] == "time_series_specialist"
    assert payload["execution"]["status"] == "VERIFIED"


def test_call_tool_energy_agent_runs_demo(engine: Engine) -> None:
    result = call_tool(engine, "agent.energy", {"demo_label": "balance"})
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["agent"] == "energy_specialist"
    assert payload["execution"]["status"] == "VERIFIED"


def test_call_tool_domain_agent_requires_demo_or_skill(engine: Engine) -> None:
    result = call_tool(engine, "agent.time_series", {})
    assert result.isError is True
    payload = _parse_content(result)
    assert "requires 'demo_label'" in payload["error"]


@pytest.mark.parametrize(
    ("preferred_domain", "expected_agent"),
    [
        ("optimization", "agent.optimization_specialist"),
        ("mathematics", "agent.applied_mathematics"),
        ("timeseries", "agent.time_series"),
        ("energy", "agent.energy"),
    ],
)
def test_call_tool_default_router_respects_preferred_domain(
    engine: Engine, preferred_domain: str, expected_agent: str
) -> None:
    demo_by_agent = {
        "agent.optimization_specialist": "diet",
        "agent.applied_mathematics": "sqrt2",
        "agent.time_series": "resample",
        "agent.energy": "balance",
    }
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "route me",
            "preferred_domain": preferred_domain,
            "demo_label": demo_by_agent[expected_agent],
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == expected_agent


def test_call_tool_default_router_respects_review_preferred_domain(engine: Engine) -> None:
    solve = _parse_content(
        call_tool(engine, "agent.optimization_specialist", {"demo_label": "diet"})
    )
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": "review this",
            "preferred_domain": "review",
            "ops_document": solve["ops"],
            "execution": solve["execution"],
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.scientific_reviewer"
    assert payload["result"]["passed"] is True


@pytest.mark.parametrize(
    ("arguments", "expected_agent"),
    [
        ({"ops": {"problem_class": "lp"}}, "agent.optimization_specialist"),
        ({"ops_document": {"problem_class": "lp"}}, "agent.optimization_specialist"),
        ({"preferred_domain": "review"}, "agent.scientific_reviewer"),
    ],
)
def test_router_target_for_ops_and_review_signals(
    arguments: dict[str, Any], expected_agent: str
) -> None:
    assert _router_target_for(arguments) == expected_agent


@pytest.mark.parametrize(
    ("skill_id", "expected_agent"),
    [
        ("optimization.lp", "agent.optimization_specialist"),
        ("timeseries.resample", "agent.time_series"),
        ("energy.balance", "agent.energy"),
        ("battery.soc_step", "agent.energy"),
        ("electrical.three_phase_balance", "agent.energy"),
    ],
)
def test_call_tool_default_router_infers_agent_from_skill_prefix(
    engine: Engine, skill_id: str, expected_agent: str
) -> None:
    assert _router_target_for({"skill_id": skill_id}) == expected_agent


@pytest.mark.parametrize(
    ("demo_label", "expected_agent"),
    [
        ("knapsack", "agent.optimization_specialist"),
        ("solve_root", "agent.applied_mathematics"),
        ("fill_missing", "agent.time_series"),
        ("soc_step", "agent.energy"),
    ],
)
def test_call_tool_default_router_infers_agent_from_demo_label(
    engine: Engine, demo_label: str, expected_agent: str
) -> None:
    assert _router_target_for({"demo_label": demo_label}) == expected_agent


def test_call_tool_default_router_raises_when_no_signal(engine: Engine) -> None:
    result = call_tool(engine, "agent.default", {"request": "do something vague"})
    assert result.isError is True
    payload = _parse_content(result)
    assert "could not infer a specialist" in payload["error"]


def test_call_tool_default_router_infers_mathematics_from_request(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": (
                "Determine o máximo e o mínimo de v(t)=t^3 - 10.5*t^2 + 30*t + 20 "
                "entre 13 e 18 horas, onde t é o número de horas após o meio-dia."
            )
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    assert payload["selected_agent"] == "agent.applied_mathematics"
    assert payload["result"]["interpreted_as"] == "scalar_extrema_on_closed_interval"


def test_call_tool_default_router_solves_clock_offset_extrema_request(engine: Engine) -> None:
    result = call_tool(
        engine,
        "agent.default",
        {
            "request": (
                "Durante várias semanas, o departamento de trânsito registrou a velocidade "
                "média v(t)=t^3 - 10,5 t^2 + 30 t + 20 km/h, onde t é o número de horas "
                "após o meio-dia. Qual o instante, entre 13 e 18 horas, em que o trânsito "
                "é mais rápido? E qual o instante em que ele é mais lento?"
            )
        },
    )
    assert result.isError is False
    payload = _parse_content(result)
    report = payload["result"]
    assert payload["selected_agent"] == "agent.applied_mathematics"
    assert report["bounds"] == [1.0, 6.0]
    assert report["offset_hours"] == 12.0
    min_x = report["min_execution"]["result"]["x"]
    max_x = report["max_execution"]["result"]["x"]
    min_value = report["min_execution"]["result"]["fun"]
    max_value = -report["max_execution"]["result"]["fun"]
    assert math.isclose(min_x, 5.0, rel_tol=0, abs_tol=1e-3)
    assert math.isclose(max_x, 2.0, rel_tol=0, abs_tol=1e-3)
    assert math.isclose(min_value, 32.5, rel_tol=0, abs_tol=1e-3)
    assert math.isclose(max_value, 46.0, rel_tol=0, abs_tol=1e-3)


def test_run_specialist_by_name_rejects_unknown_agent_tool(engine: Engine) -> None:
    """Defensive branch: unreachable through call_tool's `_AGENT_TOOL_SCHEMAS`
    gate, but guards `_run_specialist_by_name` itself against misuse."""
    with pytest.raises(ValueError, match="Unknown agent tool"):
        _run_specialist_by_name(engine, "agent.not_a_real_agent", {})


def test_call_tool_unknown_skill_fails_gracefully(engine: Engine) -> None:
    result = call_tool(engine, "mathematics.not_a_real_skill", {})
    assert result.isError is True
    payload = _parse_content(result)
    assert "error" in payload or "code" in payload
    # Must not raise — the MCP session stays up.


def test_mcp_conforms_to_engine_run(engine: Engine) -> None:
    """ADR 0005: same inputs via Engine.run and MCP call_tool yield the same
    scientific content (status + numeric result). Transport-only fields
    (run_id, timestamps) may differ across the two executions.
    """
    inputs = {"expression": "x**2 - 2", "bracket": [0, 2]}
    sdk_result = engine.run("mathematics.solve_root", inputs)
    mcp_result = call_tool(engine, "mathematics.solve_root", inputs)

    assert mcp_result.isError is False
    payload = _parse_content(mcp_result)
    assert payload["status"] == sdk_result.status.value
    assert math.isclose(
        payload["result"]["root"],
        sdk_result.result["root"],
        rel_tol=1e-12,
    )
    # Diagnostics/method identity should match for the same deterministic skill.
    assert payload["method"]["id"] == sdk_result.method.id
    assert payload["diagnostics"]["converged"] is sdk_result.diagnostics["converged"]


def test_build_server_registers_handlers(engine: Engine) -> None:
    server = build_server(engine)
    assert server.name == "oec"
    # Handlers are registered on the low-level Server request map.
    assert mcp_types.ListToolsRequest in server.request_handlers
    assert mcp_types.CallToolRequest in server.request_handlers


def test_registered_handler_reports_invalid_input_in_band(engine: Engine) -> None:
    """Regression guard (independent review of Sprint 07): the mcp SDK's
    call_tool() decorator pre-validates `arguments` against the tool's
    inputSchema *before* the handler runs, by default -- for a schema
    violation, that short-circuits straight to a bare isError=True
    result with no ExecutionResult at all, silently diverging from
    ADR 0005 (the SDK/CLI/REST all deliver a schema violation as an
    in-band ExecutionStatus.INVALID, not a transport-level error).
    build_server() registers with validate_input=False specifically so
    OEC's own pipeline stays the source of truth for INVALID -- this
    test drives the actual registered handler (server.request_handlers),
    not the inner call_tool() function directly, which is exactly the
    layer the original bug lived in and every other test in this file
    bypasses."""
    server = build_server(engine)
    handler = server.request_handlers[mcp_types.CallToolRequest]

    request = mcp_types.CallToolRequest(
        params=mcp_types.CallToolRequestParams(
            name="mathematics.solve_root",
            arguments={
                "expression": "x**2 - 2",
                "bracket": [0, 2],
                "unexpected_field": True,  # violates input.schema.json's additionalProperties
            },
        )
    )
    server_result = anyio.run(handler, request)

    result = server_result.root
    assert isinstance(result, mcp_types.CallToolResult)
    assert result.isError is False
    payload = json.loads(result.content[0].text)
    assert payload["status"] == "INVALID"


def test_run_stdio_server_warms_and_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entrypoint builds/warms Engine and hands off to anyio without a real stdio."""
    ran: dict[str, bool] = {}

    def fake_run(func: Any, *args: Any, **kwargs: Any) -> None:
        ran["called"] = True

    monkeypatch.setattr("oec.mcp.server.anyio.run", fake_run)
    run_stdio_server(skills_root="skills")
    assert ran.get("called") is True


def test_call_tool_oec_error_from_run_is_error_result(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If Engine.run raises OECError after the tool was listed, surface as error."""
    from oec.errors import SkillNotFoundError

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise SkillNotFoundError("gone", details={"skill_id": "mathematics.solve_root"})

    monkeypatch.setattr(engine, "run", boom)
    result = call_tool(
        engine,
        "mathematics.solve_root",
        {"expression": "x - 1", "bracket": [0, 2]},
    )
    assert result.isError is True
    payload = _parse_content(result)
    assert payload["code"] == "skill_not_found"
    assert "message" in payload


def test_call_tool_non_dict_arguments_fails_gracefully(engine: Engine) -> None:
    """call_tool() is a public, directly-callable surface whose whole
    point is 'never raise' -- a non-dict `arguments` (not reachable
    through the real MCP transport, which types this as dict | None,
    but reachable if called directly, as this test does) must not crash
    it (independent review of Sprint 07)."""
    result = call_tool(engine, "mathematics.solve_root", ["not", "a", "dict"])  # type: ignore[arg-type]
    assert result.isError is True
    payload = _parse_content(result)
    assert "error" in payload


def test_exports_from_package() -> None:
    from oec.mcp import build_server as exported_build
    from oec.mcp import run_stdio_server as exported_run

    assert exported_build is build_server
    assert exported_run is run_stdio_server
