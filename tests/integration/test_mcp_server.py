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
    LIST_SKILLS_TOOL_NAME,
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


def test_list_tools_includes_skills_and_list_skills(engine: Engine) -> None:
    tools = build_tools(engine)
    by_name = {tool.name: tool for tool in tools}

    assert LIST_SKILLS_TOOL_NAME in by_name
    assert by_name[LIST_SKILLS_TOOL_NAME].inputSchema == {
        "type": "object",
        "properties": {},
    }

    skill_ids = {m.id for m in engine.registry.list_skills(include_retired=False)}
    assert "mathematics.solve_root" in skill_ids
    for skill_id in skill_ids:
        assert skill_id in by_name

    # inputSchema is the skill's real schema, not a hand-written copy.
    loaded = engine.registry.get_skill("mathematics.solve_root")
    assert by_name["mathematics.solve_root"].inputSchema == loaded.input_schema
    assert by_name["mathematics.solve_root"].description == (
        loaded.manifest.description or loaded.manifest.title
    )

    # One tool per skill + list_skills.
    assert len(tools) == len(skill_ids) + 1


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
