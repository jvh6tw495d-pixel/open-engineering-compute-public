# ADR 0023: Authoritative-answer envelope, `claimed_answer` channel, MCP-only scope

- **Status:** accepted
- **Date:** 2026-08-03
- **Phase:** v2.5.3, Waves 1–5 (`docs/implementation/v2.5.3-EXECUTION-PLAN.md`)

## Context

`oec.mcp` agent tools (`agent.*`) historically returned nine distinct live
response shapes: `needs_clarification`, `needs_more_information`,
`SpecialistReport`, `SkillAgentReport`, `MathRequestReport` (dual
`min_execution`/`max_execution`), `ReviewReport`, the `agent.default` router
wrapper, a bare `ExecutionResult` for raw-skill tool calls, and a structured
error body. A host (host agent, Odysseus, or any local-LLM-driven client) had to
scrape the path-specific nesting for each shape to find the final number.
Real weak-model stress testing (`docs/implementation/
OLLAMA_AGENT_STRESS_TEST_REPORT.md` and predecessors, D-CUR-22 through
D-CUR-25) repeatedly showed a weak host narrating a *correct* OEC solve into
an *incorrect* final JSON answer — not because OEC computed the wrong
number, but because the host's own re-serialization step corrupted it.
Tracked as D-CUR-26 (`docs/implementation/technical-debt.md`).

Threat model this ADR addresses: a weak local model, given a completely
correct `ExecutionResult`, produces a wrong final answer when asked to
restate it as JSON. Not addressed: OEC computing a wrong answer in the first
place (that is a solver-correctness problem, out of scope here), or a
malicious host (there is no MCP authentication/authorization story yet,
D-CUR-10).

## Decision

### 1. Wrap-once, additive envelope (Wave 1)

`src/oec/mcp/envelope.py::normalize()` runs exactly once, at the
`call_tool` boundary (`src/oec/mcp/server.py`), for every tool name present
in `_AGENT_TOOL_SCHEMAS`. It never runs inside `_run_specialist_by_name`,
which recurses for `agent.default`'s router path — running it there too
would double-wrap the router's nested result.

Normalization is **additive**: every existing key (including the router's
`payload["result"]` nesting) is preserved unchanged; normalized keys
(`authoritative_answer`, `authoritative_answer_schema_version`,
`problem_classification`, `method_summary`, `status: "ok"`, `selected_agent`)
are mirrored at the top level. Zero edits were made to any pre-existing
test asserting the old nesting. Raw-skill tool calls (bare `ExecutionResult`,
outside `_AGENT_TOOL_SCHEMAS`) are never touched — their `ExecutionStatus`
surface is untouched by this release.

`authoritative_answer` is present only when an execution actually minted
one: `INVALID`/`FAILED` statuses omit it (never a null placeholder —
*absence* is the signal), and `needs_clarification`/`needs_more_information`
never carry it. `authoritative_answer.values` is `execution.result`
**verbatim** for a single execution; the one structural exception is dual
`min_execution`/`max_execution` (free-text scalar extrema), closed into
`kind: "scalar_extrema_result"` with an explicit `{min, max}` shape — this
was judged worth a named shape rather than forcing free-text math results
through the single-execution path. Review reports use `kind: "review_result"`
from `passed` + `checks[]`, never a synthesized fake `execution`. `kind` is
a closed v1.0 taxonomy (skill-id prefix → kind, `generic_result` fallback) —
schema'd in `schemas/authoritative_answer.schema.json`.

### 2. `claimed_answer` channel, fail-closed divergence (Wave 2)

Every `_AGENT_TOOL_SCHEMAS` entry declares an optional `claimed_answer`
property (unconstrained JSON, `{}` in the input schema). This is **not** a
new MCP tool and does not change how any tool is invoked — a host may
voluntarily state what it believes the answer is, alongside its normal
arguments, and OEC checks that belief against what it just computed.

`src/oec/mcp/divergence.py` compares `claimed_answer` against
`authoritative_answer` **after** both sides round-trip through the same
canonical serialization the MCP transport itself uses
(`json.dumps(..., sort_keys=True, separators=(",", ":"), default=str)`) —
never on pre-serialization Python objects, so tuple-vs-list and dict-key
order never produce a false mismatch. Numeric comparison uses versioned
tolerance (`DEFAULT_ABS_TOLERANCE = 1e-9`, `DEFAULT_REL_TOLERANCE = 1e-6`
via `math.isclose`); `NaN`/`±Infinity` are always flagged
(fail-closed — these don't round-trip losslessly through JSON, so OEC
cannot verify the claim and refuses to guess). A claim may cover only a
subset of `authoritative_answer.values`: an authoritative key the claim
doesn't mention is not compared; a claimed key OEC never produced is
flagged. `DIVERGENCE_POLICY_VERSION = "1.0"` is carried on every
`host_output_diverged` and must bump on any tolerance/rule change (a host
may depend on today's silence/firing behavior at the margin).

On disagreement, OEC adds a structured `host_output_diverged` warning
(`policy_version`, `reason`, `mismatches[]` with per-field paths). **This
never changes `authoritative_answer`** — under no circumstance does a
host's claim override OEC's own computation; `host_output_diverged` is
purely an additive signal that the host's own downstream state has already
drifted from what OEC computed.

`agent.scientific_reviewer`'s existing narrow `claimed_objective`/
`claimed_solver_status` fields (which feed the reviewer's own `checks[]`,
predating this release) are unaffected and coexist with the new, generic
`claimed_answer` channel — they answer different questions and are not
merged.

### 3. Benchmark harnesses read the envelope, not host prose (Wave 3)

`scripts/_oec_authority.py` (`read_authority`, `three_verdicts`) is the
shared helper new/updated harnesses (`multiagent_with_without_oec.py`
and host-integration supertests) use to classify each run as
`transport_failure`, `oec_execution_failure`, or `host_corruption` — the
last one specifically by comparing a run's parsed host prose against the
authority probe's own answer via the same fail-closed comparison policy
`oec.mcp.divergence` runs in production. The `with_oec_agent` arm's number
comes from `authoritative_answer`, never from scraping the host's free-text
JSON. Four older single-score scripts (`direct_model_supertest.py`,
`hard_lp_supertest.py`, `multiagent_llm_benchmark.py`,
`llama_oec_experiment.py`) were marked `STALE vs 2.5.3` in their module
header rather than migrated — they predate the three-verdict model and
would need a redesign, not a patch, to report it honestly.

### 4. Scope: MCP agent tools only

This release touches `oec.mcp`'s `agent.*` tool surface exclusively. REST
(`src/oec/api/app.py`), the SDK (`oec.sdk.Engine`), the CLI (`oec run`),
and raw (non-`agent.*`) MCP skill tools are **not** in scope — none of them
have the "weak host re-narrates a JSON body" failure mode this ADR
addresses (REST/SDK/CLI callers consume `ExecutionResult` directly; raw MCP
skill tools already return it verbatim with no specialist narration layer
in between). Expanding the envelope to those surfaces in the same release
was explicitly rejected as scope creep (plan §16, §11 item 6) and is a
candidate for a future ADR if a concrete host need appears there.

## Non-goals (this release)

- Perfecting free-text domain routing accuracy (D-CUR-23) — a separate,
  pre-existing heuristic-tuning problem `claimed_answer`/divergence
  detection does not touch.
- Curated per-domain `authoritative_answer.values` subsets — `values` stays
  `execution.result` verbatim; no per-domain allowlist/renaming.
- MCP authentication, authorization, or rate limiting (D-CUR-10) — a
  malicious host is out of this release's threat model.
- Unit conversion during `claimed_answer` comparison — a `kW`/`MW` mismatch
  on an otherwise-matching `QuantityValue`-shaped claim is a plain string
  mismatch on `unit`, not resolved by OEC.
- Any change to `ExecutionStatus` (ADR 0007), `ExecutionResult`'s frozen
  shape, or the count/identity of MCP tools exposed.

## Consequences

- A host that only reads `authoritative_answer` (ignoring narrative) gets a
  stable, closed-taxonomy JSON surface across all nine response shapes,
  additively layered onto the exact bytes it already received in 2.5.2.
- A host that also sends `claimed_answer` gets a free, fail-closed
  consistency check against its own downstream state, without OEC ever
  trusting that claim over its own computation.
- Wave 4 live smoke (`docs/implementation/v2.5.3-WAVE4-SMOKE-REPORT.md`)
  is the acceptance evidence that a weak host reading `authoritative_answer`
  actually gets the right number where it previously didn't.
- Residual, explicitly not closed by this ADR: whether a *specific* real
  host (host agent, Odysseus, or a third party) actually changes its own
  integration code to read `authoritative_answer` instead of continuing to
  parse narrative text is outside OEC's control — the contract is
  published (`docs/contracts/authoritative-answer.md`,
  `docs/mcp/README.md`) and schema'd, but host-side adoption is a residual
  integration item (see D-CUR-26's closure note).
