"""MCP server: expose every registered OEC skill as an MCP tool (ADR 0015).

Thin adapter over :class:`oec.sdk.Engine` — translates MCP tool list/call
into Engine operations and returns :class:`~oec.execution.models.ExecutionResult`
JSON as-is (ADR 0005). No method selection, no extra validation, no result
reshaping.
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

LIST_SKILLS_TOOL_NAME = "list_skills"
_LIST_SKILLS_INPUT_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}
_LIST_SKILLS_DESCRIPTION = "List registered OEC skill manifests (mirrors `oec skills list --json`)."


def _json_text(payload: Any) -> TextContent:
    """Serialize ``payload`` as a single MCP text content block."""
    return TextContent(type="text", text=json.dumps(payload, default=str))


def _error_result(message: str, *, details: dict[str, Any] | None = None) -> CallToolResult:
    """Build a failed tool result without raising (keeps the MCP session alive)."""
    body: dict[str, Any] = {"error": message}
    if details is not None:
        body["details"] = details
    return CallToolResult(content=[_json_text(body)], isError=True)


def build_tools(engine: Engine) -> list[Tool]:
    """One MCP :class:`~mcp.types.Tool` per registered skill, plus ``list_skills``.

    Each skill tool's ``inputSchema`` is that skill's own ``input.schema.json``
    (loaded via the registry), not a hand-written copy — ADR 0015.
    """
    tools: list[Tool] = []
    for manifest in engine.registry.list_skills(include_retired=False):
        skill = engine.registry.get_skill(manifest.id, manifest.version)
        description = skill.manifest.description or skill.manifest.title
        tools.append(
            Tool(
                name=skill.manifest.id,
                description=description,
                inputSchema=skill.input_schema,
            )
        )
    tools.append(
        Tool(
            name=LIST_SKILLS_TOOL_NAME,
            description=_LIST_SKILLS_DESCRIPTION,
            inputSchema=dict(_LIST_SKILLS_INPUT_SCHEMA),
        )
    )
    return tools


def call_tool(engine: Engine, name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Dispatch a tool call against ``engine``.

    Sync on purpose: :meth:`Engine.run` already serializes executions
    (ADR 0015); the MCP handler just waits if another call is in progress.
    """
    if name == LIST_SKILLS_TOOL_NAME:
        manifests = engine.registry.list_skills(include_retired=False)
        payload = [m.model_dump(mode="json", by_alias=True) for m in manifests]
        return CallToolResult(content=[_json_text(payload)], isError=False)

    try:
        engine.registry.get_skill(name)
    except OECError:
        return _error_result(f"Unknown tool: {name!r}", details={"tool": name})

    try:
        result = engine.run(name, arguments)
    except OECError as exc:
        # SkillNotFoundError (and other OECError subclasses) must not crash
        # the MCP session — surface them as a structured error tool result.
        return CallToolResult(content=[_json_text(exc.to_dict())], isError=True)

    return CallToolResult(
        content=[_json_text(result.model_dump(mode="json"))],
        isError=False,
    )


def build_server(engine: Engine) -> Server[Any, Any]:
    """Wire ``engine`` into a low-level MCP :class:`~mcp.server.lowlevel.Server`.

    Uses the low-level API (not FastMCP) so each skill's pre-built JSON Schema
    dict can be passed as ``inputSchema`` verbatim — FastMCP derives schemas
    from Python type annotations and cannot accept arbitrary JSON Schema.
    """
    server: Server[Any, Any] = Server("oec", version=__version__)

    # mcp's list_tools/call_tool decorators ship without precise stubs under
    # strict mypy -- the exact error code raised (untyped-decorator vs.
    # no-untyped-call vs. misc) depends on exactly which mcp version
    # resolves, which differs between this venv and pre-commit's isolated
    # mypy environment (same cross-environment stub-drift issue as
    # src/oec/kernel/optimization/constrained.py hit in Sprint 05) -- a
    # bare ignore (not code-scoped) is what stays valid across both.
    @server.list_tools()  # type: ignore
    async def list_tools() -> list[Tool]:
        return build_tools(engine)

    @server.call_tool()  # type: ignore
    async def handle_call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
        return call_tool(engine, name, arguments)

    return server


def run_stdio_server(skills_root: str | Path = "skills") -> None:
    """Build a warmed :class:`~oec.sdk.Engine` and serve skills over MCP stdio.

    Entrypoint for the future ``oec server mcp`` CLI command (Sprint 07 Fase C).
    """
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
