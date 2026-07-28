# MCP server

Exposes an OEC default router first, then specialist agents, then raw OEC skills, plus fixed discovery
tools. Thin adapter over `oec.sdk.Engine` and the repository's `agents/`
companion layer.

Default policy: when a host inspects the OEC MCP catalog, it should prefer the
`agent.default` router. Raw skill tools remain available for explicit low-level
calls when the caller intentionally names a specific function.

Design rationale: [ADR 0015](../architecture/adr/0015-rest-mcp-contract.md).

## Requirements

```bash
uv sync --extra mcp
```

## Run

```bash
oec server mcp --skills-root skills
```

Or from Python:

```python
from oec.mcp import run_stdio_server

run_stdio_server(skills_root="skills")
```

Entrypoint: `oec.mcp.server.run_stdio_server` (also re-exported as
`oec.mcp.run_stdio_server`).

## Tools

| Tool | Purpose |
|---|---|
| `agent.default` | Main OEC entrypoint. Generic requests should go here so OEC chooses the right specialist. |
| `agent.optimization_specialist` | Default LP/MILP path. Accepts a full OPS document or `demo_label`, validates, executes `optimization.lp`/`optimization.milp`, and narrates from `ExecutionResult` only. |
| `agent.scientific_reviewer` | Audits OPS + `ExecutionResult` without re-solving. |
| `agent.applied_mathematics` | Domain wrapper over math / linear / statistics / numerical skills. |
| `agent.time_series` | Domain wrapper over `timeseries.*` quality and grid skills. |
| `agent.energy` | Domain wrapper over public energy / battery / electrical skills. |
| `list_agents` | Specialist-agent catalog. Preferred discovery entrypoint for hosts. |
| `list_skills` | Raw skill catalog, mirroring `oec skills list --json`. |
| `<skill_id>` | Run a specific low-level skill directly. `inputSchema` is the skill's own `input.schema.json`. Result is the full `ExecutionResult` JSON. |

## Recommended host behavior

1. Consult `list_agents` first.
2. Use `agent.default` by default.
3. Let the router choose a specialist agent unless the caller explicitly asks for a specific raw function.
4. Only call a raw `<skill_id>` when the user explicitly asks for that specific function.

## Out of scope (Alpha)

Authentication, authorization, and rate-limiting are intentionally not
implemented. Do not expose this server to untrusted networks as shipped.
Concurrent tool calls on one `Engine` instance are serialized (one execution at
a time); that is expected, not a bug.
