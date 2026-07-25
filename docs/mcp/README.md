# MCP server

Exposes every registered OEC skill as an MCP tool, plus a fixed
`list_skills` discovery tool. Thin adapter over `oec.sdk.Engine` — same
`ExecutionResult` JSON as the CLI/SDK/REST path (ADR 0005).

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
| `<skill_id>` (one per registered skill) | Run that skill. `inputSchema` is the skill's own `input.schema.json`. Result is the full `ExecutionResult` JSON (`status`, `result`, `diagnostics`, `warnings`, `provenance`, …). |
| `list_skills` | Skill catalog — same manifest list as `oec skills list --json`. |

Example skill tools today: `mathematics.solve_root`,
`mathematics.integrate`, `mathematics.interpolate`,
`mathematics.optimize_scalar`, `mathematics.optimize_constrained`,
`mathematics.curve_fit`.

## Out of scope (Alpha)

Authentication, authorization, and rate-limiting are intentionally not
implemented — see ADR 0015 §4. Do **not** expose this server to untrusted
networks as shipped. Concurrent tool calls on one Engine instance are
serialized (one skill subprocess at a time); that is expected, not a bug.
