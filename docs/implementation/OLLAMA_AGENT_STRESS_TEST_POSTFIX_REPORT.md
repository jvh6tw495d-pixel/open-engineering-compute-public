# Ollama agent stress test — post-audit-correction rerun

**Date:** 2026-07-30 (JSON `generated_at` reads `2026-07-31T01:45:19+00:00` — same UTC/local offset note as the pre-fix report)
**Kind:** reliability / robustness run — not an accuracy leaderboard
**Driver model:** `nemotron-3-nano:4b-64k` via Ollama native tool calling (`http://127.0.0.1:11434`)
**Server under test:** OEC MCP stdio server, working tree with Corrections A and B applied (`src/oec/mcp/server.py::_has_execution_payload`, `agents/optimization_specialist/specialist.py::run_skill`)
**Harness:** [scripts/ollama_agent_stress_test.py](../../scripts/ollama_agent_stress_test.py)
**Raw data:** [docs/implementation/OLLAMA_AGENT_STRESS_TEST_POSTFIX_RESULTS.json](OLLAMA_AGENT_STRESS_TEST_POSTFIX_RESULTS.json)
**Baseline this supersedes:** [OLLAMA_AGENT_STRESS_TEST_REPORT.md](OLLAMA_AGENT_STRESS_TEST_REPORT.md) (pre-fix, same 41-prompt battery, see its addendum)

## Why this rerun exists

`docs/implementation/oec-agent-router-post-audit-corrections.md` (an independent
audit) found two real bugs in the pre-fix router: an empty/hallucinated
`execution: {}` could hijack `agent.default` routing to the reviewer over a
valid `ops`/`preferred_domain` signal (Correction A), and the discovery
fallback's own promised `skill_id`+`inputs` retry for
`agent.optimization_specialist` was a dead end (Correction B). Both were
fixed and covered by new deterministic unit/integration tests. This rerun
re-validates transport stability and structured-error behavior against a
live model after those fixes, per the audit's stated closing criterion.

## Headline

Completed successfully end-to-end, same shape as the pre-fix run:

- the MCP server stayed alive through the full 41-prompt battery;
- the post-run concurrency probe completed cleanly (8 parallel calls, 6.11s);
- `fatal_harness_error` is empty — no timeout, no crash, no hang;
- every one of the 9 tool-side errors came back in OEC's structured
  `oec_error_result` shape (`error_shape_ok: true`, 9/9);
- no `ModuleNotFoundError: No module named 'agents'` surfaced;
- server stderr at the end contains only "not listed, no validation" notices
  for hallucinated tool names — no traceback.

## Top-line numbers

| Metric | Value |
|---|---:|
| Prompts | 41 |
| Tool calls executed | 40 |
| `isError: false` | 31 |
| `isError: true` | 9 |
| Structured OEC error shapes | 9 / 9 |
| Unstructured / SDK-generic tool errors | 0 |
| Concurrency probe calls | 8 |
| Concurrency probe wall clock | 6.112 s |
| Server alive after run | true |
| Total wall clock | 683.7 s |
| Fatal harness error | none |

## What the 9 errors actually were

None of them are the two bugs this rerun set out to check for. In order:

1. `optimization.llp` — hallucinated skill id (typo of `optimization.lp`), unknown-tool error.
2. `optimization_optimizer_specialist` — hallucinated tool name, unknown-tool error.
3. `agent.optimizer_specialist` — hallucinated tool name (×2 across the run), unknown-tool error.
4. `agent.scientific_reviewer` called **directly** by the model (not routed through `agent.default`) with a shallow pseudo-`execution` object (missing `status`/`skill`/`method`/`started_at`) — `ExecutionResult` pydantic validation correctly rejects it. This is explicitly out of scope for Correction A (requirement 5: the reviewer's own direct-call contract was deliberately left unchanged) and is the expected, correct behavior.
5. `agent.energy` with an empty `demo_label`.
6. `agent.standard` — hallucinated tool name.
7. `agent.default` on prompt 27, `"Do the thing with the numbers."`, with no `preferred_domain` and no other signal — the router's honest `"could not infer a specialist"` error. Zero domain signal in the text; this is the documented, still-open D-CUR-23 limitation (ambiguous prompts), not a regression.

**Zero occurrences of `"agent.optimization_specialist requires 'ops' or 'demo_label'"`** anywhere in this run's errors — the exact dead-end string Correction B removed.

## Did this run reproduce the two specific bugs live?

**Correction B (discovery-loop dead end): indirectly confirmed working.**
Two `agent.default` calls (prompts 28 and 39) hit the free-text fallback path
for `agent.optimization_specialist` and both came back `isError: false` with
`status: "needs_more_information"` and real candidates — the same code path
Correction B's retry mechanism depends on. No call in this run happened to
retry with `skill_id`+`inputs` against the optimization specialist (the
model didn't choose to), so this run doesn't exercise the retry leg live —
that's what `test_optimization_agent_skill_id_plus_inputs_retry_closes_the_
discovery_loop` in `tests/integration/test_mcp_server.py` is for, and it
passes.

**Correction A (`execution: {}` hijack): not reproduced live, by design of
what a 4B model does.** No prompt in this run happened to combine `ops`/
`preferred_domain` with a hallucinated `execution: {}` in the same
`agent.default` call — prompt 25 came close (`ops: {}` + `demo_label`,
correctly handled by the pre-existing `execute_ops` "out_of_scope" path,
unrelated to the `execution` key) but didn't include `execution` at all.
Matches this test suite's own prior finding: small local models are "poor
fuzzers" — they don't reliably reproduce narrow, specific bug combinations
on demand. The deterministic tests
(`test_has_execution_payload_rejects_empty_or_incomplete_dicts`,
`test_router_target_for_empty_execution_does_not_outrank_real_signals`,
`test_call_tool_default_router_knapsack_request_with_empty_execution_does_
not_hit_reviewer`) are what actually prove this fix; this run's job was to
confirm it didn't destabilize anything else, which it didn't.

## Comparison to the pre-fix run

| | Pre-fix | Post-fix |
|---|---:|---:|
| Prompts | 41 | 41 |
| Tool calls | 40 | 40 |
| `isError: false` | 30 | 31 |
| `isError: true` | 9 | 9 |
| Structured error shapes | 9/9 | 9/9 |
| `agent.default` calls | 7 | 4 |
| `"requires 'ops' or 'demo_label'"` errors | 0 (already fixed by prior discovery work before this specific string check existed as a target) | 0 |
| Fatal harness error | none | none |
| Total wall clock | 692.84s | 683.7s |

Numbers are close but not identical prompt-for-prompt — this is a live,
non-deterministic small model choosing its own tool calls each time (not a
replay), consistent with every other rerun in this project's history.
Transport stability and structured-error behavior are both confirmed
unchanged (still 100%) after the corrections.

## Honest assessment

This rerun does not "prove" Correction A works from live model behavior
alone — it couldn't, because the specific input pattern it fixes wasn't
reproduced this run. What it does prove: the fixes didn't regress anything
observable in a real 41-prompt, mixed-workload run (transport stayed up,
error shape stayed structured, the specific dead-end string it removed
didn't reappear), and one of the two fixes (the discovery fallback path
Correction B extends) is directly visible working in prompts 28 and 39.
Confidence in Correction A specifically rests on its deterministic tests,
not this run — which is the expected division of labor between unit/
integration tests (prove the specific fix) and a stress run (prove nothing
else broke).

## Reproducing

```text
.venv\Scripts\python.exe scripts\ollama_agent_stress_test.py --json-out docs\implementation\OLLAMA_AGENT_STRESS_TEST_POSTFIX_RESULTS.json
```
