# Ollama agent stress test report

**Date:** 2026-07-30 (JSON `generated_at` reads `2026-07-31T00:54:45+00:00` — that's the same instant in UTC; the run happened the night of 2026-07-30 local time (America/Sao_Paulo, UTC-3), which is the date used everywhere else in this session's artifacts)
**Kind:** reliability / robustness run — not an accuracy leaderboard
**Driver model:** `nemotron-3-nano:4b-64k` via Ollama native tool calling (`http://127.0.0.1:11434`)
**Server under test:** OEC MCP stdio server launched with the real host runtime shape
**Harness:** [scripts/ollama_agent_stress_test.py](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\scripts\ollama_agent_stress_test.py)
**Raw data:** [docs/implementation/OLLAMA_AGENT_STRESS_TEST_RESULTS.json](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\docs\implementation\OLLAMA_AGENT_STRESS_TEST_RESULTS.json)

## Why this rerun exists

The previous Markdown report and the current JSON artifact had drifted out of sync after a later aborted run overwrote the JSON. This rerun re-established a clean pair of synchronized artifacts.

The harness was also updated to force `uv` to use a cache and temp directory inside the repository working tree, avoiding Windows permission failures under `C:\Users\joaop\AppData\Local\uv\cache`.

## Headline

This rerun completed successfully end-to-end.

- the MCP server stayed alive through the full 41-prompt battery;
- the post-run concurrency probe completed cleanly;
- `list_agents` still worked after the full run;
- every tool-side error came back in OEC's structured JSON error shape;
- no `ModuleNotFoundError: No module named 'agents'` surfaced.

That means the runtime patch for agent importability is holding under the real host runtime-style launch condition.

## Launch shape used

The server was launched from `C:\Windows` on purpose, not from the repo root, to preserve the failure mode that originally broke `agent.*`.

Command family:

```text
uv.exe --directory <repo> run --extra mcp --extra optimization oec server mcp --skills-root <repo>\skills
```

Environment overrides injected by the harness:

- `UV_CACHE_DIR=<repo>\.uv-cache`
- `TMP=<repo>\.stress-tmp`
- `TEMP=<repo>\.stress-tmp`

These overrides are now recorded in the JSON artifact under `server_launch.env_overrides`.

## Top-line numbers

| Metric | Value |
|---|---:|
| Prompts | 41 |
| Model turns | 77 |
| Tool calls executed | 40 |
| `isError: false` | 30 |
| `isError: true` | 9 |
| Structured OEC error shapes | 9 / 9 |
| Unstructured / SDK-generic tool errors | 0 |
| Prompts with no tool call | 15 |
| Concurrency probe calls | 8 |
| Concurrency probe wall clock | 6.511 s |
| Server alive after run | true |
| Total wall clock | 692.84 s |

Server stderr at the end contained only near-miss tool warnings:

- `Tool 'agent.standard' not listed, no validation will be performed`
- `Tool 'energy.energy_balance' not listed, no validation will be performed`

No traceback was emitted by the server during the completed run.

## Category breakdown

| Category | Prompts | Calls | ok | err | no tool |
|---|---:|---:|---:|---:|---:|
| optimization | 5 | 8 | 5 | 2 | 0 |
| review | 4 | 3 | 2 | 1 | 1 |
| mathematics | 5 | 8 | 6 | 2 | 1 |
| timeseries | 5 | 5 | 5 | 0 | 1 |
| energy | 5 | 10 | 7 | 3 | 1 |
| ambiguous_multidomain | 6 | 2 | 1 | 1 | 4 |
| malformed_numeric | 6 | 3 | 3 | 0 | 3 |
| offtopic | 5 | 1 | 1 | 0 | 4 |

## What this run validates

### 1. Runtime import fix is holding

The server was deliberately started from outside the repo root and still served `agent.*` traffic. This is the real test for `_ensure_agents_importable()` in [src/oec/mcp/server.py](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\src\oec\mcp\server.py).

### 2. Structured error contract is holding

All 9 failures were emitted as `oec_error_result`.

That means the client saw structured payloads instead of generic SDK text, even under noisy model behavior and wrong tool names.

### 3. The server remained stable under a mixed workload

This run included:

- raw skills
- `agent.*` routes
- discovery calls
- near-miss tool hallucinations
- a post-run concurrency probe

The session survived the entire sequence and still answered `list_agents` at the end.

## What changed versus the older report

The previous report described a world where `agent.default` free-text was mostly a dead end. That is no longer an accurate description of the current working tree.

In this rerun:

- `agent.default` was called 7 times
- 5 calls returned `isError: false`
- 2 calls returned structured errors

So the free-text path is no longer "always bounce with ValueError". It now often degrades into:

- `out_of_scope`, or
- `needs_more_information`

instead of hard-failing.

This matches the new fallback in [src/oec/mcp/discovery.py](C:\Users\joaop\OneDrive\Anexos de email\Documentos\OEC\src\oec\mcp\discovery.py).

## Current `agent.default` reality

The current behavior is improved, but not perfect.

### Non-error outcomes observed

Examples from the rerun:

- optimization-style request routed to `agent.optimization_specialist` and returned `out_of_scope` with missing OPS fields instead of crashing
- energy-style malformed requests returned `needs_more_information` plus ranked candidate skills and example payloads
- nonsense optimization prompt still returned a structured `needs_more_information` candidate list instead of a hard failure

### Remaining bad cases observed

Two notable failures remain:

1. a free-text request still produced:
   - `agent.default could not infer a specialist`

2. one `agent.default` call surfaced a structured `ValidationError` involving `ExecutionResult`

So the router is better, but still not fully robust across vague or malformed requests.

## Most important residual risks

### 1. `agent.default` is better, but still not universally dependable

The improvement is real, but the ambiguous/multidomain bucket still had weak coverage:

- 6 prompts
- only 2 tool-call executions
- 4 prompts answered without ever calling a tool

That means the combined "LLM chooses tools + router interprets generic intent" path is still fragile under vague multi-step asks.

### 2. The fallback ranking is heuristic

The new discovery path is clearly better than hard failure, but it is still keyword-overlap ranking. That is good enough for graceful recovery, not yet a proof of best-skill selection quality.

### 3. Review payloads are still easy for the model to get wrong

One reviewer call failed with structured `ValidationError` because the model provided a shallow pseudo-execution object rather than a real `ExecutionResult`-shaped payload.

So the system is resilient, but reviewer ergonomics remain demanding.

## Honest assessment

This is a good result.

Not because the model became brilliant — it did not. It still hallucinated:

- `agent.standard`
- `energy.energy_balance`
- bad demo labels

The good result is that the OEC MCP surface now absorbs that noise without collapsing into unstructured failure.

The strongest validated claims from this rerun are:

1. the `agents` import/runtime fix is real;
2. the structured MCP error contract is real;
3. the free-text fallback path now exists and is observable in practice;
4. the server remains stable under mixed noisy traffic.

The main claim that is still only partially true is:

- "`agent.default` is now a strong generic entrypoint"

It is no longer a dead end, but it is not yet consistently decisive for vague multidisciplinary prompts.

## Recommendation

Treat the current state as:

- **transport/runtime stable**
- **error handling strong**
- **free-text router materially improved**
- **generic orchestration still maturing**

The next best follow-up is not another giant refactor. It is targeted hardening:

1. add more integration coverage for vague multi-domain prompts
2. improve `agent.default` handling of reviewer-oriented free text
3. keep the structural packaging follow-up for `agents/` on the roadmap, because `_ensure_agents_importable()` is still a pragmatic runtime patch, not a final architecture

## Reproducing

```text
.venv\Scripts\python.exe scripts\ollama_agent_stress_test.py
```

Quick pass:

```text
.venv\Scripts\python.exe scripts\ollama_agent_stress_test.py --limit 12
```

The harness now manages its own local cache/temp directories inside the repository, so it should be much less sensitive to Windows permission issues than before.

## Addendum (post-audit correction, 2026-07-30, later same night)

This report's two "remaining bad cases" both got fixed after this run, in a
follow-up pass driven directly by this report's own findings plus an
independent audit (`docs/implementation/oec-agent-router-post-audit-
corrections.md`):

1. **The `execution: {}` ValidationError case (residual risk #3):** the
   router (`_router_target_for` in `src/oec/mcp/server.py`) now only treats
   `execution` as a review signal via `_has_execution_payload()`, which
   requires the dict to actually have `status`/`skill`/`method`/
   `started_at`. A hallucinated `execution: {}` alongside a clear `ops` or
   `preferred_domain` signal no longer gets diverted to
   `agent.scientific_reviewer`.
2. **The optimization discovery-fallback dead end:** `agent.optimization_
   specialist` accepted only `ops`/`demo_label`, so retrying with
   `skill_id`+`inputs` (exactly what this report's own fallback payload told
   the caller to do) failed with `"requires 'ops' or 'demo_label'"`.
   `OptimizationSpecialist.run_skill()` (`agents/optimization_specialist/
   specialist.py`) now closes that loop, restricted to `optimization.*`
   skill ids.

Both fixes are covered by new tests in `tests/integration/test_mcp_server.py`
and have since been re-validated against a live Ollama rerun — see
[OLLAMA_AGENT_STRESS_TEST_POSTFIX_REPORT.md](OLLAMA_AGENT_STRESS_TEST_POSTFIX_REPORT.md).
Short version: transport stayed stable, all errors stayed structured, and
the specific `"requires 'ops' or 'demo_label'"` dead-end string this fixed
did not reappear — but the live run's small model didn't happen to
reproduce the exact `execution: {}` hijack combination on its own, so
Correction A's confidence still rests primarily on its deterministic tests,
not this rerun. See that report's own "Honest assessment" section.
