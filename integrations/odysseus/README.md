# Odysseus integration (optional)

Wire [Odysseus](https://github.com/) (or any MCP-capable agent host) to an
OEC MCP server so agents can **discover** and **run** engineering skills
with full methodology, units, diagnostics and provenance — without the
OEC core depending on Odysseus.

The core package installs and runs with **zero** Odysseus dependencies.
Everything in this folder is configuration, examples and smoke checks.

## Prerequisites

```bash
# from the OEC repository root
uv sync --extra mcp
```

OEC MCP entrypoint (stdio):

```bash
oec server mcp --skills-root skills
```

See also [`docs/mcp/README.md`](../../docs/mcp/README.md) and
[ADR 0015](../../docs/architecture/adr/0015-rest-mcp-contract.md).

## Success criteria (handbook §15.1)

1. Start OEC MCP (`oec server mcp`).
2. Point Odysseus at the local (or remote) MCP config.
3. List skills (`list_skills` tool).
4. Run a calculation (any skill tool, e.g. `mathematics.solve_root` or
   `electrical.three_phase_power`).
5. Receive methodology metadata, numeric result, diagnostics and
   provenance inside the standard `ExecutionResult` JSON.

## Files

| File | Purpose |
|---|---|
| `local-mcp.example.json` | Stdio MCP server block for a local OEC checkout |
| `remote-mcp.example.json` | HTTP/streamable placeholder once remote transport ships |
| `docker-compose.example.yml` | Optional containerized OEC API sidecar |
| `examples.md` | Natural-language → tool call walkthroughs |
| `tutorial.md` | Step-by-step §15.1 success path (Fase 7) |
| `tests/` | Config smoke + MCP adapter e2e (no Odysseus binary required) |

## Security

Alpha MCP has **no authentication and no rate limiting** (ADR 0015 §4).
Do not expose it on untrusted networks. Prefer stdio on the same host
as Odysseus.
