# Technical debt

**Current-state review:** 2026-08-07 at `oec==3.3.1` (updated from the prior
2026-07-30 `oec==2.5.2` review — see
[3.3.1-phase0-3-execution-report.md](3.3.1-phase0-3-execution-report.md) and
[3.3.1-phase4-5-execution-report.md](3.3.1-phase4-5-execution-report.md) for
what changed between those two points: physics/multiphysics co-simulation
(2.6–2.7), chemistry foundation + Scientific IR + Model Registry (2.8–2.9),
chemistry completion + THD + sequential chemistry network (3.1–3.3.0), and
the 3.3.1 catalog/gate recovery). The 3.3.1 recovery pass directly verified
D-CUR-21 through D-CUR-27 (the `agent.default`/MCP routing family) plus the
skill-catalog/quality-gate items are still accurate as of `3.3.1` (see the
two reports above for evidence). Items outside that pass's scope (sandbox
isolation, REST/MCP auth, coverage/telemetry items below) were not
re-audited in this update — their "still open" status is carried forward,
not re-verified, and should not be read as fresher than the review date on
each row.

This file began as a Phase A snapshot. Historical entries remain for
traceability; the current queue below is the canonical starting point for new
work. An item is not closed merely because a later roadmap mentions it — each
closure below cites the commit/file that actually did it.

## Current queue

| ID | Priority | Item | Target / evidence |
|---|---|---|---|
| D-AI-01 | P1 | PEFT / full fine-tune train skills not implemented (schema frozen in ADR 0038) | **3.6 S1** — ADR 0041; `docs/release/SCIENTIFIC-AI-3.6.md` |
| D-AI-02 | P1 | Knowledge distillation skill missing | **3.6 S2** — `neural.distill` + builder; ADR 0041 |
| D-AI-03 | P2 | VLM / multimodal foundation path missing | **3.6 S5** — ADR 0040 D3 |
| D-AI-04 | P2 | vLLM / llama.cpp / SGLang adapters not planned for 3.6 | **Debt only** — HF Transformers is the 3.6 inference backend; ADR 0040 D2 |
| D-AI-05 | P3 | NEAT / HyperNEAT productization | **Excluded from 3.6 DoD** — ADR 0042 (re-open only with new ADR) |
| D-AI-06 | P2 | Neural checkpoint/file reload + industrial status promotion incomplete | **3.6 S3** — SCIENTIFIC-AI-3.6 |
| D-AI-07 | P2 | Optional CI job for `neural`/`evolutionary`/`foundation` extras | **3.6 S6** |
| D-CUR-02 | P1 | Default five-second skill timeout can be consumed by a cold SciPy import on Windows | Still open — measure and decide import/warmup versus timeout policy before public distribution |
| D-CUR-07 | P1 | `diagnostics_from_mapping` (`src/oec/core/diagnostics.py`) heuristic coverage is thin | Still open — core hardening |
| D-CUR-08 | P1 | `oec.core.provenance.ProvenanceRecord` permits untyped extra passthrough (`extra="allow"`) | Still open by design (ADR 0017); revisit only if it starts hiding real schema drift |
| D-CUR-09 | P1 | No OS-level memory/network/filesystem isolation | Still open — pre-untrusted deployment; ADR 0012 |
| D-CUR-10 | P1 | REST/MCP have no authentication or rate limiting | Still open — confirmed current in `docs/api/README.md` and `docs/mcp/README.md`'s own "not yet implemented" sections |
| D-CUR-11 | P2 | `SkillLifecycle.validate_transition` (`src/oec/skills/lifecycle/lifecycle.py`) is unused outside its own test | Still open — confirmed via repo-wide reference search |
| D-CUR-12 | P2 | Runner subprocess paths have limited direct coverage instrumentation | Still open — `src/oec/execution/runner.py` at 73% (crash/timeout branches uncovered) |
| D-CUR-13 | P2 | Development telemetry/cost per accepted task is not implemented | Still open — operations roadmap |
| D-CUR-15 | P2 | No Git tags or remote; “release” currently means private commit milestone | Still open — explicit release-governance decision |
| D-CUR-20 | P2 | `check_bound_conflicts`/empty-coefficient precheck branches in `src/oec/kernel/optimization/feasibility.py`'s three public functions appear unreachable — `validate_ops` (called first in all three) already rejects the same malformed input earlier | Still open — needs a design decision (remove as dead code / find an undiscovered call path / relax `validate_ops`), not a coverage fix; see `tests/unit/test_kernel_optimization_feasibility.py`'s module docstring |
| D-CUR-21 | P1 | `agents/` (Optimization Specialist, Scientific Reviewer, Applied Mathematics, Time-Series, Energy) is a dev-only PEP 420 namespace package living outside `src/oec`, importable only when the repo root is on `sys.path` — broke every `agent.*` MCP tool call under the real Hermes launcher (`ModuleNotFoundError: No module named 'agents'`). Correction: this did *not* crash the stdio session — the `mcp` SDK's own `Server.call_tool` handler already catches any escaping exception and returns `isError=True`; the real damage was that it bypassed this codebase's own structured `{"error", "details": {"tool", "error_type"}}` shape (`_error_result`) in favor of the SDK's generic plain-text message, dropping the tool name and error type | Runtime patched 2026-07-30 — `oec.mcp.server._ensure_agents_importable()` resolves the repo root from its own `__file__` and appends it to `sys.path` at import time, independent of the caller's cwd/`PYTHONPATH` (regression test `tests/integration/test_mcp_server.py::test_agent_tools_importable_outside_repo_root_cwd`, reproduces via a real subprocess; verified live against Hermes's actual `mcp_servers.oec` launch command: `uv --directory … run --extra mcp --extra optimization oec server mcp`). Separately, `call_tool()` (`src/oec/mcp/server.py`) now also catches unexpected exceptions (not just `OECError`/`ValueError`/`TypeError`) on both the agent-dispatch and raw-skill-dispatch paths and returns them in the structured shape (`test_call_tool_unexpected_exception_from_specialist_is_structured_error`, `test_call_tool_unexpected_exception_from_engine_run_is_structured_error`) — this is the fix for the actual observed damage, not the `sys.path` patch. Independent-review caveat from 2026-07-30 (now closed): the broad `except Exception` blocks originally swallowed the traceback with no logging; both now call `_logger.exception(...)` (`src/oec/mcp/server.py`, `logging.getLogger(__name__)`) before returning the structured error, so a genuine specialist coding bug is still recorded server-side even though the client only sees the one-line message. Also, `sys.path.append` (not `insert(0, ...)`) means a real installed `agents` distribution (e.g. an unrelated `agents` PyPI package) would silently shadow the repo's companion package and this fix would no-op — not currently the case in this repo's environment, but worth a guard if it ever is. Structural fix still open: move `agents/` under `src/oec/agents/` (or ship it as an installable companion package) so agent-mode stops depending on a `sys.path` patch |
| D-CUR-22 | P1 | `agent.default` — the documented default, agent-first entrypoint — was a dead end for free-text `request` in 4 of 5 domains: `_router_target_for`/`_infer_domain_from_request` correctly inferred the domain, but `_run_specialist_by_name` only accepted `demo_label` or explicit `skill_id`+`inputs` for every specialist except `AppliedMathematicsSpecialist` (and only for a narrow regex-based scalar-extrema grammar there), so the bare `request` string was rejected downstream with `ValueError`. Confirmed independently three times on 2026-07-30: by a memory note recording a prior (never-committed) investigation, by a real Ollama-driven stress test (`docs/implementation/OLLAMA_AGENT_STRESS_TEST_REPORT.md` — 4/5 real `agent.default` calls failed identically), and by an Opus/Fable design review. Separately, `_infer_domain_from_request`'s `"lp" in text`/`"ops" in text` were bare substrings, misrouting any request containing "he**lp**" or "sh**ops**"/"dr**ops**" into the optimization domain | Fixed 2026-07-30 — new `src/oec/mcp/discovery.py` (`rank_candidate_skills`, `build_skill_suggestion_payload`): when a specialist gets a `request` it can't act on, it now returns a non-error `{"status": "needs_more_information", "candidates": [...]}` payload (each candidate carries its real `input.schema.json` plus a worked example from the skill's `examples/` dir) instead of raising, wired into all four gap points in `_run_specialist_by_name` (`src/oec/mcp/server.py`) including a try/except around `AppliedMathematicsSpecialist.run_request` so its parser failures degrade to suggestions too. `_infer_domain_from_request` now matches tokens via `_contains_token` (leading `\b` word boundary, no trailing boundary so deliberate stems like `"restri"`/`"autocorrelat"` keep working) instead of bare substring search. Tests: `tests/unit/test_mcp_discovery.py` (ranking, example-loading, payload shape) plus `tests/integration/test_mcp_server.py` (one fallback test per specialist, the `_contains_token`/`_infer_domain_from_request` word-boundary regression, and the pre-existing AR-keyword-routing parametrized test updated from "must error" to "must return needs_more_information") |
| D-CUR-23 | P2 | The original token-overlap ranking and orphan-domain gap from D-CUR-22 | Partially fixed 2026-07-30 in v2.5.2 — `rank_domain_intents` now uses deterministic weighted id/title/tag/description evidence; low-confidence or tied free text returns structured `needs_clarification`; `agent.control_dynamics` and `agent.finance_uncertainty` now cover the previously orphaned families. Still open: weights and aliases are curated heuristics, not a semantic classifier; add a versioned golden routing corpus and telemetry before tuning them from real usage. |
| D-CUR-24 | P1 | `_router_target_for` treated bare *presence* of an `execution` key as a review signal (`"execution" in arguments`), so a local LLM hallucinating an empty/placeholder `execution: {}` alongside an otherwise clear optimization request (`ops` + `preferred_domain`) got diverted to `agent.scientific_reviewer`, which then failed validating the empty payload — even though `ops`/`preferred_domain` pointed at a perfectly runnable specialist. Confirmed by an independent audit (`docs/implementation/oec-agent-router-post-audit-corrections.md`) and reproduced by the real Ollama stress test's residual-risk #3 (`OLLAMA_AGENT_STRESS_TEST_REPORT.md`, one reviewer call failed with `ValidationError` from a shallow pseudo-execution object) | Fixed 2026-07-30 — new `_has_execution_payload(arguments)` in `src/oec/mcp/server.py` requires `execution` to be a `dict` containing `status`/`skill`/`method`/`started_at` before it counts as a review signal; `_router_target_for` uses it in place of the bare key check. Existing precedence (`ops`/`ops_document` → `preferred_domain` → `skill_id` → `demo_label` → `request` inference → honest error) was already in the right order, so no reordering was needed. `agent.scientific_reviewer` called directly is unchanged (still requires `execution` present; full `ExecutionResult` validation stays the reviewer's job, not the router's). Tests: `tests/integration/test_mcp_server.py::test_has_execution_payload_rejects_empty_or_incomplete_dicts`, `test_router_target_for_empty_execution_does_not_outrank_real_signals`, `test_call_tool_default_router_knapsack_request_with_empty_execution_does_not_hit_reviewer` (the real stress-test failure shape: knapsack request + `preferred_domain` + `ops` + `execution: {}` all in one call). Live post-fix Ollama rerun (`OLLAMA_AGENT_STRESS_TEST_POSTFIX_REPORT.md`) confirms no regression but did not independently reproduce this exact input combination — the 4B driver model didn't happen to combine `execution` with other signals this run; confidence rests on the deterministic tests above, per that report's own "Honest assessment" |
| D-CUR-25 | P1 | The D-CUR-22 discovery fallback tells callers to retry a specialist with `skill_id`+`inputs` from its `candidates` payload, but `agent.optimization_specialist` only ever accepted `ops` or `demo_label` — the retry loop was a dead end (`"agent.optimization_specialist requires 'ops' or 'demo_label'"`), confirmed by the same independent audit and by `OLLAMA_AGENT_STRESS_TEST_REPORT.md`'s "current `agent.default` reality" section | Fixed 2026-07-30 — new `OptimizationSpecialist.run_skill(skill_id, inputs)` (`agents/optimization_specialist/specialist.py`) runs an explicit skill via `Engine.run`, restricted to `optimization.*` (anything else raises a clear `ValueError`, surfaced as `call_tool`'s usual structured error); wired into `agent.optimization_specialist`'s dispatch in `src/oec/mcp/server.py`. Returns a `SkillAgentReport`-shaped dict (`agent`/`skill_id`/`inputs`/`execution`/`narrative`/`notes`) — the same shape the other three specialists already use for their own `skill_id`+`inputs` path — which differs from `execute_ops`/`run_demo`'s `SpecialistReport` shape (`problem_class`/`ops`/`assumptions`/...); this cross-path shape difference already existed for every other specialist's `ops`-vs-`skill_id` split and is not new here. Tests: `test_optimization_agent_skill_id_plus_inputs_retry_closes_the_discovery_loop` (full cycle: request → candidate → retry, both directly and routed through `agent.default`), `test_optimization_agent_rejects_skill_id_outside_its_domain`, `test_call_tool_default_router_optimization_request_returns_optimization_candidates`. Live post-fix Ollama rerun (`OLLAMA_AGENT_STRESS_TEST_POSTFIX_REPORT.md`) confirms the discovery-fallback path itself works live (2 real `agent.default` calls returned `needs_more_information` with real candidates) and the old `"requires 'ops' or 'demo_label'"` dead-end string did not reappear anywhere in 40 tool calls; the live model didn't happen to attempt the `skill_id`+`inputs` retry leg itself, which is what the deterministic full-cycle test covers |
| D-CUR-27 | P2 | v2.5.3's `authoritative_answer` envelope (D-CUR-26, ADR 0023) is deliberately scoped to `oec.mcp` agent tools only. Three residual gaps outside that scope, none silent: (1) REST (`src/oec/api/app.py`) and the SDK (`oec.sdk.Engine`)/CLI (`oec run`) callers get the raw `ExecutionResult` with no envelope/`claimed_answer`/divergence support at all -- a REST client re-narrating a result into wrong JSON has no server-side safety net; (2) `authoritative_answer.values` is `execution.result` verbatim by design (no curated/renamed per-domain subset) -- a caller wanting a stable field name independent of each skill's own result schema still has to know each skill's shape; (3) no authentication/rate-limiting on MCP (D-CUR-10) means the `claimed_answer` channel and this whole hardening story assume a non-malicious host, not an adversarial one | Open -- explicit scope decision (ADR 0023 non-goals + plan §16), not an oversight. Revisit REST/SDK/CLI envelope extension only if a concrete caller need appears (ADR 0023); curated-values subsetting only if a specific skill's raw result shape proves unusable for a real host; MCP auth is D-CUR-10's separate, pre-existing item |
| D-CUR-26 | P1 | MCP agent tools historically emitted nine distinct live response shapes (clarification, skill suggestion, SpecialistReport, SkillAgentReport, MathRequestReport dual min/max, ReviewReport, router wrapper, bare ExecutionResult for raw skills, structured error). Hosts and weak local LLMs had to scrape path-specific nesting and could corrupt correct solver results when re-emitting final JSON | Closed 2026-08-03 in v2.5.3 (Waves 1-4; ADR 0023) -- `src/oec/mcp/envelope.py` normalizes agent-tool responses once at the `call_tool` boundary (Wave 1: additive top-level `authoritative_answer`/`problem_classification`/`method_summary`/`status: ok`, scoped to `_AGENT_TOOL_SCHEMAS` only; raw-skill `ExecutionStatus` untouched); `src/oec/mcp/divergence.py` adds host-voluntary `claimed_answer` + fail-closed `host_output_diverged` comparison (Wave 2); `scripts/_oec_authority.py` + `hermes_supertest.py`/`multiagent_with_without_oec.py` read the envelope instead of scraping host prose, classifying transport/OEC/host-corruption verdicts separately (Wave 3); `schemas/authoritative_answer.schema.json` v1.0 + `docs/contracts/authoritative-answer.md` publish the contract. Live weak+strong smoke: `docs/implementation/v2.5.3-WAVE4-SMOKE-REPORT.md`. **Residual (not closed by this item, tracked separately):** whether a specific real host (Hermes, Odysseus, third party) actually changes its own integration code to read `authoritative_answer` instead of continuing to parse narrative text is outside OEC's control -- the contract is published and schema'd, adoption is not enforceable from the server side; REST/SDK/CLI remain out of scope for the envelope by design (ADR 0023 non-goals) |


## Recently closed

| ID | Closed | Evidence |
|---|---|---|
| D-CUR-01 | 2026-07-27 | core independence probe now runs in a fresh interpreter; full suite 810 passed |
| D-CUR-03 | 2026-07-27 | V3 gap map reconciled with shipped `oec.core` and `ScientificResult` |
| D-CUR-04 | 2026-07-27 | Graphify rebuilt from `6e271496` before work; rebuild again at handoff |
| D-CUR-16 | 2026-07-27 | installation smoke now retains complete child stdout/stderr and separately proves installed CLI/sandbox and numerical backend execution |
| D-CUR-05 | 2026-07-27 | `scripts/audit_physical_units.py` added — automated bare-physical-float authoring gate, 9 skills scanned, 0 errors (v2.1, commit `abb31c7`) |
| D-CUR-06 | 2026-07-27 | `energy.balance`, `energy.load_metrics`, `battery.soc_step` migrated to `QuantityValue`-only physical contracts, skill version `0.2.0` (v2.1, commit `abb31c7`) |
| D-CUR-14 | 2026-07-28 | Backend Capability Registry (`src/oec/backends/{registry,capabilities,selection,fallback}.py`) + Verification Engine (`src/oec/verification/{engine,report}.py`) shipped and operational, ADR 0021 (commit `5b35ae4`, corrected `1f2efa0`) |
| — | 2026-07-28 | v2.5 golden-set distribution gate closed — every V3-plan domain bucket now meets its minimum (see `docs/implementation/v2.5-golden-set-expansion.md`) |
| — | 2026-07-28 | v2.5 critical-path coverage measured for the first time: 90% aggregate, meets the gate (see `docs/implementation/v2.5-critical-path-coverage.md`; the kernel-specific shortfall this surfaced is tracked as D-CUR-19 above, not closed) |
| — | 2026-07-28 | v2.5 public-API docstring coverage measured and closed: 87.8% → 100%, `scripts/audit_public_api_docs.py` added (see `docs/implementation/v2.5-public-api-docs-audit.md`) |
| — | 2026-07-28 | `forbidden_names` gate back to zero hits — reworded `v2.4-team-brief.md`'s stray forbidden-list word |
| — | 2026-07-29 | v2.4/v2.5 release metadata closeout: package version `2.3.0 → 2.5.0`, `CHANGELOG.md` v2.5.0 entry, README status, `docs/implementation/skill-inventory.md` reconciled (`40 → 63` skills) |
| D-CUR-19 | 2026-07-30 | `src/oec/kernel/` package coverage raised 86% → 91.4% via a targeted push on the 4 weakest modules (`timeseries.quality` 67%→100%, `timeseries.ops` 68%→96%, `timeseries.timegrid` 70%→100%, `optimization.feasibility` 77%→84%); now clears the 90% critical-path bar (v2.5.1, commit `45c06e9`) |
| — | 2026-07-30 | v2.5.1 refinement release: AR/autocorrelation package (`timeseries.{autocorrelation,pacf,ar_yule_walker,levinson_durbin}`), `agent.default` routing extension, `docs/implementation/skill-inventory.md` reconciled again (`63 → 67` skills), package version `2.5.0 → 2.5.1` |

## Historical Phase A view

Ranked for **Phase A only**. Items that only matter for OPS/HiGHS/agents are listed as post-A.

## P0 — must address in Phase A (A1–A3)

| ID | Item | Why | Target |
|---|---|---|---|
| D-A1-01 | No `input_hash` in provenance | Reproducibility claim incomplete | A1 |
| D-A1-02 | No explicit backend name/version in provenance | Cannot prove SciPy/Pint versions per run | A1 |
| D-A1-03 | ExecutionResult contract not in `docs/contracts/` | Agents/humans guess shape | A1 |
| D-A1-04 | Skill versioning policy not written | Breaking schema changes ambiguous | A1 |
| D-A2-01 | No hard limits on payload / array length | **Done A2** — `oec.execution.limits` | A2 ✓ |
| D-A2-02 | Sandbox overclaim risk | **Done A2** — `docs/contracts/execution-limits-and-sandbox.md` | A2 ✓ |
| D-A3-01 | ADR 0005 sample only math | Electrical path less proven across 4 UIs | A3 |
| D-A3-02 | No automated multi-skill contract test | Drift of top-level result keys | A3 |

## P1 — document in A, fix later if needed

| ID | Item | Notes |
|---|---|---|
| D-P1-01 | No OS-level memory/network/fs isolation | ADR 0012 deferred; honest docs in A2 |
| D-P1-02 | `assumptions` / `conventions` often empty lists | Content lives in `skill.md`; auto-fill optional |
| D-P1-03 | `SkillLifecycle.validate_transition` unused at runtime | Not blocking Alpha core |
| D-P1-04 | `runner.py` coverage across process boundary | Known; not Phase A blocker |
| D-P1-05 | Dev telemetry (cost per task) | Old plan §19; out of A |
| D-P1-06 | Working tree hygiene for future features | A0 establishes process |

## P2 — post–Phase A (do not pull into A)

| ID | Item |
|---|---|
| D-P2-01 | HiGHS / LP / MILP / OPS |
| D-P2-02 | Specialist agents |
| D-P2-03 | Pluggable backend protocol for all skills |
| D-P2-04 | Time series, energy, finance skills |
| D-P2-05 | Rename `mathematics` → `math` |
| D-P2-06 | Real multi-tenant sandbox |

## Error codes currently defined (`oec.errors`)

| Code | Class |
|---|---|
| `oec_error` | `OECError` |
| `skill_error` | `SkillError` |
| `skill_not_found` | `SkillNotFoundError` |
| `skill_manifest_invalid` | `SkillManifestError` |
| `skill_frontmatter_invalid` | `SkillFrontMatterError` |
| `skill_entrypoint_invalid` | `SkillEntrypointError` |
| `skill_version_conflict` | `SkillVersionConflictError` |
| (+ validation / execution subclasses) | see `errors.py` full module |

Phase A1: inventory completeness check only; add codes only if a real gap appears.
