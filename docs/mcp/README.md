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
directory — e.g. host agent launching `uv run oec server mcp` with its own cwd —
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
| `agent.control_dynamics` | Domain wrapper over public `control.*` and `dynamics.*` skills. |
| `agent.finance_uncertainty` | Domain wrapper over public `finance.*` and `uncertainty.*` skills. |
| `agent.neural` | Neural & evolutionary specialist: public `neural.*` and `evolutionary.*` skills (ADR 0031 / ADR 0033 training + search). Prefer this for MLP/LSTM/CNN/transformer, neuroevolution, NSGA/DE/CMA-ES. Raw skill tools (`neural.mlp.regressor`, `evolutionary.optimize_single`, …) remain in the catalog. |
| `experiment.run` | Multi-step `ExperimentSpec` runner (W2). Returns `ExperimentRecord` with metrics and validation. |
| `list_agents` | Specialist-agent catalog. Preferred discovery entrypoint for hosts. |
| `list_skills` | Raw skill catalog, mirroring `oec skills list --json`. |
| `<skill_id>` | Run a specific low-level skill directly. `inputSchema` is the skill's own `input.schema.json`. Result is the full `ExecutionResult` JSON. |

## Recommended host behavior

1. Consult `list_agents` first.
2. Use `agent.default` by default.
3. Let the router choose a specialist agent unless the caller explicitly asks for a specific raw function.
4. Only call a raw `<skill_id>` when the user explicitly asks for that specific function.
5. If a response comes back with `status: "needs_more_information"`, retry the same agent with a `skill_id` + `inputs` picked from `candidates` — don't treat it as a failure.
6. If a response comes back with `status: "needs_clarification"`, ask the user the returned questions and retry `agent.default` with supplied information only; never invent missing numeric inputs.
7. When a solved agent response includes `authoritative_answer`, treat that object as the machine-readable numerical truth — do not rebuild objective values, trajectories, or feasibility from prose or from free-form host narration.

## Canonical agent-tool envelope (`authoritative_answer`)

As of v2.5.3 Wave 1, every **agent tool** response that successfully executed a
computation (or review) is additively normalized at the `call_tool` boundary
(`src/oec/mcp/envelope.py`). Existing nesting is preserved — in particular
`agent.default` still nests the specialist report under `result` — and the
normalized keys are **mirrored at the top level**.

Raw skill tools (`<skill_id>`) are **not** wrapped: their top-level `status`
remains an `ExecutionStatus` (`VALIDATED`, `FAILED`, …). The new agent-tool
`status: "ok"` is scoped to `agent.*` only.

Example (optimization, direct or routed — same `authoritative_answer.values`):

```json
{
  "status": "ok",
  "router": "agent.default",
  "selected_agent": "agent.optimization_specialist",
  "problem_classification": {
    "domain": "optimization",
    "problem_class": "lp",
    "confidence": 1.0,
    "reason": "demo_label=diet"
  },
  "method_summary": {
    "specialist": "agent.optimization_specialist",
    "skill": "optimization.lp",
    "backend": "highs",
    "review_applied": false
  },
  "authoritative_answer_schema_version": "1.1",
  "authoritative_answer": {
    "kind": "optimization_result",
    "values": { "...execution.result verbatim..." },
    "provenance": {
      "run_id": "...",
      "input_hash": "...",
      "solver_status": "..."
    }
  },
  "result": { "...nested specialist report (shape 7 only)..." },
  "narrative": "optional, non-authoritative"
}
```

Rules hosts should rely on:

| Field | Role |
|---|---|
| `authoritative_answer` | Machine authority. Present only when an execution status is not `INVALID`/`FAILED` (or for review: always `kind: "review_result"` with `passed` + `checks`). **Absence** (not `null`) is the signal that no authority was minted. |
| `authoritative_answer.values` | For single executions: `execution.result` **verbatim**. For free-text scalar extrema: closed `{ "min": ..., "max": ... }` shape with `kind: "scalar_extrema_result"`. |
| `problem_classification` / `method_summary` / `narrative` | Explanation only — never override `authoritative_answer`. |
| `status: "needs_clarification"` / `"needs_more_information"` | No `authoritative_answer`. Do not invent numbers. |

`kind` taxonomy (v1.1, prefix → kind, fallback `generic_result`):
`optimization_result`, `mathematics_result`, `linear_result`,
`statistics_result`, `numerical_result`, `timeseries_result`,
`energy_result`, `physics_result`, `control_dynamics_result`,
`finance_uncertainty_result`, `scalar_extrema_result`, `review_result`,
`generic_result`.

Schema **1.1** is additive over **1.0**: every v1.0 kind remains valid;
`physics_result` is the sole new enum member (v2.6 Wave 4 / D3). The
published schema accepts `authoritative_answer_schema_version` of either
`"1.0"` or `"1.1"`; the boundary emits the maximum supported version
(`"1.1"`). Prefix map highlights:

| Skill prefix | `kind` |
|---|---|
| `electrical.*` / `energy.*` / `battery.*` | `energy_result` (unchanged — includes `electrical.dc_power_flow` and v2.6.1 energy-rich skills) |
| `thermal.*` / `mechanics.*` / `fluids.*` / `materials.*` | `physics_result` (new) |

Implementation: wrap-once in `call_tool` for `name in _AGENT_TOOL_SCHEMAS`
only — never inside `_run_specialist_by_name` (which recurses for the router).

### Energy-rich skills (v2.6.1 Wave 2)

New public skills under existing prefixes (no new MCP tools, no new AA kinds):

| Skill | Role | Path |
|---|---|---|
| `energy.hybrid_balance` | Multiperiod hybrid residual | `oec.physics.hybrid` |
| `energy.grid_zero_feasibility` | Deterministic trajectory check (no solver) | `oec.physics.grid_zero` |
| `energy.min_storage_capacity` | Min capacity LP (grid-zero sizing) | composes `optimization.lp` |
| `energy.pv_power` | Instantaneous PV power | `oec.physics.pv` |
| `energy.service_metrics` | Energy delivered + autonomy hours | `oec.physics.service_metrics` |
| `battery.soc_trajectory` | Multi-step energy-based SOC | `oec.physics.storage` |

`energy.grid_zero_feasibility` and `energy.min_storage_capacity` are **distinct
contracts** (feasibility of a provided trajectory vs optimization sizing).
Both map to `authoritative_answer.kind == "energy_result"`; values are
`execution.result` **verbatim** (0 double-wrap). Discovery aliases in
`src/oec/mcp/discovery.py` include PV / BESS / grid-zero / autonomy vocabulary
for free-text domain ranking.

## Host claims and divergence (`claimed_answer`, v2.5.3 Wave 2)

Every `agent.*` tool accepts an optional `claimed_answer` argument — a host
may voluntarily state what it believes the answer is, in any JSON shape.
This is **not** a new tool and does not change how a tool is called; it is
just one more optional property alongside `demo_label` / `skill_id` /
`inputs` / etc.

OEC compares the claim against the `authoritative_answer` it just computed
(post-serialization, with numeric tolerance — see
`docs/contracts/authoritative-answer.md` for the full comparison policy) and,
on disagreement, adds a `host_output_diverged` warning:

```json
{
  "host_output_diverged": {
    "policy_version": "1.0",
    "reason": "value_mismatch",
    "mismatches": [
      {
        "path": "$.objective_value",
        "reason": "value_mismatch",
        "authoritative": 1.0,
        "claimed": -999999.0
      }
    ]
  }
}
```

**`authoritative_answer` is never overwritten by a claim.** This is
fail-closed advisory only: absence of `host_output_diverged` means either no
claim was sent, or it matched; its presence flags disagreement without OEC
ever preferring the host's number over its own. Hosts should treat this the
same way they'd treat any other warning — surface it, don't silently trust
the claim, and keep reading `authoritative_answer` as the numeric truth.

## host agent / host app integration guide (short version)

For any host driving `agent.*` tools — host agent, host app, or a third party —
the whole contract above reduces to two rules:

1. **Read `authoritative_answer`.** After a successful agent-tool call, the
   number/values a host presents to its user (or feeds into a downstream
   step) should come from `response["authoritative_answer"]["values"]`, not
   from re-parsing the specialist's `narrative` string or any nested report
   text. This is true whether the call went through `agent.default`
   (routed) or a specialist directly — both paths mirror the identical
   `authoritative_answer` shape.
2. **`claimed_answer` is optional, not required.** A host that already has
   its own downstream JSON pipeline may attach `claimed_answer` to the same
   call to get a free `host_output_diverged` consistency check against
   OEC's own computation (see above). A host with no such pipeline can
   simply omit it — nothing else changes.

Live weak+strong smoke evidence for this guidance:
`docs/implementation/v2.5.3-WAVE4-SMOKE-REPORT.md`.

## Out of scope (Alpha)

Authentication, authorization, and rate-limiting are intentionally not
implemented. Do not expose this server to untrusted networks as shipped.
Concurrent tool calls on one `Engine` instance are serialized (one execution at
a time); that is expected, not a bug.
