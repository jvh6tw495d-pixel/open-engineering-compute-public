# ADR 0015: REST API and MCP contract — status mapping, tool exposure, concurrency

- **Status:** accepted
- **Date:** 2026-07-25

## Context

Sprint 07 adds the last two of the four interfaces ADR 0005 names: a
REST API (`src/oec/api/`) and an MCP server (`src/oec/mcp/`), both
scaffolded-empty since Sprint 00. ADR 0005's acceptance bar is explicit
— the same `ExecutionRequest` submitted through any interface yields
the same scientific content, and neither interface may select a
method, apply validation, reshape results, or hold state the others
don't have. Both new interfaces wrap `oec.sdk.Engine` (Sprint 06)
exactly as the CLI's `oec run` already does — no new validator-wiring
story, no new execution logic.

Three genuinely new questions arise the moment a *network-facing*
interface exists that didn't apply to the CLI/SDK:

1. How does `ExecutionStatus` (a seven-value graded outcome, ADR 0007)
   map onto HTTP status codes, which are a binary-ish success/failure
   signal by convention?
2. How does a registered skill become discoverable/callable as an MCP
   tool?
3. `ExecutionService` spawns one subprocess per skill call (ADR 0012),
   with **no** OS-level network/filesystem/memory isolation — deferred
   explicitly to a future hardening sprint. ADR 0012 itself flags the
   risk: *"Acceptable for the Alpha's synchronous, one-skill-at-a-time
   execution model (plan section 13.3: 'execução síncrona no Alpha');
   revisit if Sprint 07's REST API needs to run many executions
   concurrently."* A REST server fielding concurrent HTTP requests is
   exactly that trigger — an unbounded, un-sandboxed subprocess spawned
   per concurrent request is a resource-exhaustion risk this project
   has no isolation story for yet.

Also folded in here: an independent review of Sprint 06 found that
`oec.sdk.Engine._services` (a plain `dict` populated lazily on first
call to a given skill) is not safe under concurrent first-calls to the
same skill — two threads racing to build the same `ExecutionService`
(which itself dynamically imports the skill's `validation.py` via
`importlib`, not reliably concurrency-safe) is a real bug once `Engine`
is shared across concurrent request threads, which REST/MCP both do.

## Decision

### 1. HTTP status ↔ `ExecutionStatus` mapping

**The run endpoint returns HTTP `200` with the full `ExecutionResult`
JSON body whenever the execution pipeline actually produced a result —
including `INVALID`, `FAILED`, and `INCONCLUSIVE`.** HTTP status codes
are reserved strictly for *transport*-level failures:

| HTTP status | Condition |
|---|---|
| `200` | The pipeline ran to completion and produced an `ExecutionResult` — regardless of `status` inside it. The caller inspects `body.status`, exactly as `oec run`'s `--json` output and `oec.sdk.Engine.run()`'s return value already require. |
| `404` | `skill_id` (or `skill_id`+`version`) does not resolve — `SkillNotFoundError`. |
| `422` | The request body itself doesn't parse (malformed JSON, wrong shape) — a framework-level (Pydantic/FastAPI) validation failure, distinct from `ExecutionStatus.INVALID` (which means the body parsed fine but the skill's own `input.schema.json` rejected the *skill inputs*). |
| `500` | An OEC-internal error the pipeline itself didn't classify (should be rare — most failure modes already route through `ExecutionStatus.FAILED` inside a `200`). |

Rationale: `INVALID`/`FAILED`/`INCONCLUSIVE` are structured *scientific*
outcomes the Execution Service already classified (ADR 0007) — encoding
that classification a second time in the HTTP status layer would push
scientific content into the transport layer, which ADR 0005 explicitly
forbids interfaces from doing. This deliberately diverges from `oec
run`'s own exit-code model (ADR 0014: `0`/`2`/`3`/`4` map to
`ExecutionStatus`) — the CLI's exit code is the *only* signal a calling
shell has without parsing a body; HTTP has a body every caller is
already expected to parse, so status-in-body is both sufficient and
the more RESTful shape (a 4xx/5xx response conventionally means "your
request was bad" or "the server broke," not "the science didn't
converge").

### 2. MCP tool-exposure convention

**One MCP tool per registered skill**, named after the skill's id
(`mathematics.solve_root` etc.), with `inputSchema` set directly to
that skill's own `input.schema.json` — the same JSON Schema
`SchemaValidator` already validates against, not a hand-maintained
copy. A tool call's result is the full `ExecutionResult`, structured
identically to the REST/CLI JSON output (ADR 0005's conformance bar
applies here too). Plus one fixed discovery tool, `list_skills`,
mirroring `oec skills list --json` / `GET /skills`.

Rejected alternative: a single generic `run_skill(skill_id, inputs)`
tool. Simpler to implement, but hides each skill's actual input shape
from MCP clients (an LLM driving the tool would have to already know
or separately discover a skill's schema) — the one-tool-per-skill
design makes every skill a first-class, self-describing MCP tool,
which matches this project's central thesis (skills are the unit of
capability, not a generic "run something" escape hatch).

### 3. Concurrency: `Engine.run()` is a single critical section

Per ADR 0012's own forward-reference and plan section 13.3's
"execução síncrona no Alpha," `oec.sdk.Engine` now serializes
**all** executions through one internal lock — at most one skill
subprocess runs at a time, across every caller sharing that `Engine`
instance, regardless of how many concurrent HTTP/MCP requests arrive.
Concretely: `Engine.run()` acquires a `threading.Lock` for its entire
body (cache lookup/build **and** `ExecutionService.execute()`), not
just the cache-building step.

This is deliberately the simplest correct answer, not a tuned
worker-pool: it fixes the `Engine._services` cache race (Sprint 06
finding) as a side effect (the lock already excludes concurrent access
to the dict), and it is the direct, honest consequence of ADR 0012's
gap — with zero OS-level resource isolation per subprocess, the only
safe concurrency bound for the Alpha is exactly what the plan already
called for: one execution at a time. A REST/MCP request arriving while
another executes simply waits; this is acceptable for the Alpha's
synchronous model and revisited only alongside real OS-level sandboxing
(ADR 0012's own deferred hardening sprint), not before.

`Engine` also gains `warm()`: eagerly calls `build_validators` for
every registered skill, single-threaded, at construction/startup time
rather than lazily on first call. This surfaces a skill's
`SkillEntrypointError` (e.g. an ambiguous or missing `validation.py`
validator, ADR 0014) at server boot, not mid-request — REST/MCP call
`Engine(...).warm()` in their startup/lifespan hook. `oec run`
(one skill, one process, exits immediately) has no reason to call
`warm()` and doesn't.

### 4. Authentication and rate-limiting are explicitly out of scope

Neither the REST API nor the MCP server implements authentication,
authorization, or rate-limiting in this sprint. This is a stated
precondition, not an oversight: alongside ADR 0012's network/
filesystem/memory isolation gaps, **this server is not safe to expose
to untrusted networks as shipped.** The concurrency lock (§3) is a
resource-exhaustion floor, not an access-control mechanism — it
prevents a flood of concurrent requests from spawning unbounded
subprocesses, but does nothing to prevent a single unauthenticated
caller from monopolizing the server. Real auth/rate-limiting is
deferred to the same future hardening sprint as OS-level sandboxing.

## Consequences

- Every "run a skill" caller (SDK, CLI, REST, MCP) inspects
  `ExecutionResult.status` the same way — no interface encodes
  scientific status in a code the caller has to special-case.
- MCP tool count scales with the skill catalog (6 tools today, growing
  every sprint) — acceptable; MCP clients are expected to enumerate
  tools dynamically, not hardcode a list.
- Throughput under concurrent load is intentionally low (one execution
  at a time, each with real subprocess-spawn overhead) — a known,
  documented Alpha-stage limitation, not a bug to be optimized around
  before the hardening sprint gives it real isolation to run
  concurrently *safely*.
- `Engine.warm()` is optional for short-lived callers (the CLI) and
  required for long-lived ones (REST/MCP) — documented per-caller, not
  a universal `Engine` constructor step, since eagerly building every
  skill's validators is wasted work for `oec run`'s single-skill,
  single-process lifetime.
