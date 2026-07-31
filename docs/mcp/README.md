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

Agent-first mode (`agent.*` tools, `list_agents`) is confirmed working when
the server is launched by an external host from an arbitrary working
directory — e.g. Hermes launching `uv run oec server mcp` with its own cwd —
not just under `pytest` run from the repo root. `oec.mcp.server` resolves the
repo root from its own file location and makes the `agents/` companion
package importable before any specialist is dispatched, so hosts do not need
to export `PYTHONPATH` or `cd` into the repository themselves. See
`tests/integration/test_mcp_server.py::test_agent_tools_importable_outside_repo_root_cwd`
and `docs/implementation/technical-debt.md` (D-CUR-21) for the remaining
structural packaging follow-up.

### Free-text `request` and `needs_more_information`

`agent.default` infers a domain from a free-text `request` and routes to the
matching specialist, but none of the specialists (except
`agent.applied_mathematics`, for a narrow scalar-extrema grammar) has a
general natural-language-to-inputs parser — there is no reliable way to turn
"optimize my battery dispatch" into a full OPS document automatically. When a
specialist receives a `request` it cannot act on directly, it does **not**
error. It returns a non-error payload:

```json
{
  "status": "needs_more_information",
  "agent": "agent.time_series",
  "request": "...",
  "hint": "...",
  "candidates": [
    {"skill_id": "...", "title": "...", "description": "...",
     "input_schema": {...}, "example_inputs": {...}}
  ]
}
```

Hosts should treat this the same way they'd treat a skill rejecting
malformed input: pick a `skill_id` from `candidates`, adapt
`example_inputs` to the actual request, and call the same agent again with
`skill_id` + `inputs`. Candidates are ranked by keyword overlap against the
skill catalog and restricted to the calling specialist's domain (see
`src/oec/mcp/discovery.py`); this is a heuristic, not a guarantee of
surfacing the single best skill first (D-CUR-23). `agent.scientific_reviewer`
is a special case — it audits a prior `ExecutionResult` rather than running
skills, so a bare `request` there returns `candidates: []` with a hint to
run another agent first and pass its result's `execution` back in.

## Tools

| Tool | Purpose |
|---|---|
| `agent.default` | Main OEC entrypoint. Generic requests should go here so OEC chooses the right specialist. |
| `agent.optimization_specialist` | Default LP/MILP path. Accepts a full OPS document (`ops`) or `demo_label` for the OPS-formulation pipeline (validates, executes `optimization.lp`/`optimization.milp`, narrates from `ExecutionResult` only) -- or an explicit `skill_id` + `inputs` to run any other `optimization.*` skill directly (this is the retry path the `needs_more_information` fallback points callers at; a `skill_id` outside `optimization.*` is rejected with a structured error). |
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
5. If a response comes back with `status: "needs_more_information"`, retry the same agent with a `skill_id` + `inputs` picked from `candidates` — don't treat it as a failure.

## Out of scope (Alpha)

Authentication, authorization, and rate-limiting are intentionally not
implemented. Do not expose this server to untrusted networks as shipped.
Concurrent tool calls on one `Engine` instance are serialized (one execution at
a time); that is expected, not a bug.
