# Graphify — structural memory of this repository

OEC uses [Graphify](https://github.com) to build and maintain a navigable
graph of the codebase, as required by section 31 of the master plan. It is a
complement to Git, tests, docs, ADRs, and type checking — not a replacement
for any of them.

## Installation found

Graphify was already installed in the user's environment as a `uv` tool:

```text
package: graphifyy
version: 0.8.39
commands exposed: graphify, graphify-mcp
```

It is **not** on `PATH` directly (no `graphify` binary outside the uv tool
shim), so every invocation in this repository goes through:

```bash
uv tool run --from graphifyy graphify <command> [args]
```

Verified with:

```bash
uv tool list                                    # showed graphifyy v0.8.39
uv tool run --from graphifyy graphify --version # -> graphify 0.8.39
uv tool run --from graphifyy graphify --help    # full command list
```

No alternative installation was created; the pre-existing one is used as-is
per the plan's instruction not to install another variant without cause.

## Backend

Local backend available and preferred, per section 31.3:

```text
Ollama
└── llama3.1:8b   (present locally — `ollama list` confirmed)
```

The initial indexing command used for this sprint (`graphify update .`) does
**not** require an LLM backend — it performs structural extraction only. The
Ollama backend becomes relevant only for `graphify label` (semantic community
naming) or `graphify query`, which are not required for Sprint 00 and are
deferred to when the graph grows large enough to need it.

## Procedure used in Sprint 00

```bash
uv tool run --from graphifyy graphify update .
```

Output:

```text
Re-extracting code files in . (no LLM needed)...
[graphify watch] Rebuilt: 143 nodes, 166 edges, 31 communities
[graphify watch] graph.json, graph.html and GRAPH_REPORT.md updated in graphify-out
```

Artifacts generated in `graphify-out/`:

| File | Purpose |
|---|---|
| `graph.json` | machine-readable graph (nodes/edges/communities) |
| `graph.html` | interactive visual graph |
| `GRAPH_REPORT.md` | human-readable summary: hubs, god nodes, communities, gaps |
| `manifest.json` | extraction manifest |
| `.graphify_labels.json`, `.graphify_root` | internal bookkeeping |
| `cache/` | extraction cache |

## Versioning decision

`graphify-out/` is **not committed** to Git (see `.gitignore`). This is now
a formal decision — see
[ADR 0010](../architecture/adr/0010-graphify-artifacts-not-versioned.md)
for the full evaluation (size, stability, absolute paths, sensitive data)
required by master plan section 31.5 before generated artifacts can be
excluded from or included in version control.

## Update policy

Per section 31.4, the graph is updated:

- at the end of each sprint;
- after any relevant structural refactor;
- after new core modules are created;
- before multi-file architectural tasks;
- before the sprint's final report.

### Last full rebuild (v2.0 handoff)

**2026-07-27** after Scientific Kernel cut + GPT construction handoff:

```bash
uv tool run --from graphifyy graphify update .
```

**Rebuild result (2026-07-27):** ~**5058 nodes**, ~**7783 edges**, ~**435 communities**
(`graph.html` skipped — over viz node limit; use `graph.json` + `GRAPH_REPORT.md`)

Indexed highlights for construction agents:

- `src/oec/core/**` (v2.0 Scientific Kernel)
- `docs/implementation/GPT_CONSTRUCTION_HANDOFF.md` (GPT builds; Grok validates)
- `docs/implementation/OEC_V3_IMPLEMENTATION_PLAN.md` (state: v2.0 done → v2.1 next)
- `docs/concepts/scientific-kernel.md`, ADR 0019

`graphify-out/` remains **gitignored** (ADR 0010). Rebuild locally before multi-agent construction sessions.

### Pre-v2.1 stabilization rebuild

Rebuilt again on **2026-07-27** before stabilization and Q0 planning.
`GRAPH_REPORT.md` records baseline commit `6e271496` with approximately
**5063 nodes**, **7787 edges** and **428 communities**. Generated artifacts
remain local and gitignored; rebuild after the stabilization/documentation
changes before handing off implementation.

**Post-stabilization/Q0 rebuild:** **5086 nodes**, **7819 edges** and
**466 communities**. The report still names committed baseline `6e271496`;
the new stabilization and Q0 files are present in the local graph but remain
uncommitted at this handoff.

### v2.1 implementation report

The report
[`v2.1-delivery-status-and-v2.5-next-steps.md`](../implementation/v2.1-delivery-status-and-v2.5-next-steps.md)
is the indexed handoff after commits `f7cbf0a` and `abb31c7`. It records:

- the complete v2.1 implementation and independent gate evidence;
- corrections made after Terra, Grok, Opus and OpenCode review;
- blockers that still prevent declaring/tagging `2.1.0`;
- the ordered Math IR, Backend Registry, Verification and v2.5 next steps.

Rebuild Graphify after changing that report so future construction agents do
not confuse technical completion with a released package version.

### v2.1 release closeout rebuild

Rebuilt on **2026-07-27** after the v2.1 metadata/documentation closeout
(version bumps to `2.1.0`, `CHANGELOG.md` entry, README status, Q0 inventory
delivery closeout, `technical-debt.md` closures). `GRAPH_REPORT.md` now
records baseline commit `7c5c4136` with **5241 nodes**, **8177 edges** and
**457 communities**; the local tool itself is now `graphifyy` v0.9.28
(previously v0.8.39 — command surface unchanged). The closeout changes are
committed as the v2.1 release commit immediately after this rebuild.

### v2.2 Math IR foundation rebuild

Rebuilt on **2026-07-27** after the v2.2 Math IR implementation
(`src/oec/modeling/`, `src/oec/backends/`, ADR 0020, `mathematics.solve_ir`,
and the associated unit/parity tests). **5496 nodes**, **8777 edges** and
**465 communities**. Package version, `CHANGELOG.md`, README status and any
tag remain unchanged in this pass — those are a separate closeout step, per
ADR 0020's own consequences section.

### v2.2 release closeout rebuild

Rebuilt on **2026-07-27** after the v2.2 metadata/documentation closeout
(version bumps to `2.2.0`, `CHANGELOG.md` entry, README status). `GRAPH_REPORT.md`
now records baseline commit `5bd11aba` with **5501 nodes**, **8783 edges** and
**475 communities**. The closeout changes are committed as the v2.2 release
commit immediately after this rebuild.

### v2.4 Backend Registry + Verification Engine rebuild (S1–S3)

Rebuilt on **2026-07-27** after implementing the v2.4 Backend Capability
Registry (`src/oec/backends/{capabilities,selection,fallback}.py` +
`adapters/`) and Verification Engine (`src/oec/verification/`), wired
additively into `ExecutionService.execute`, plus ADR 0021. This rebuild
lands on top of `oec==2.3.0` (Applied Math expansion, Waves A+B+C), released
by a separate session on this same branch between the v2.2 closeout and this
work — the corpus grew accordingly. **7898 nodes**, **11810 edges** and
**623 communities**. Package version, `CHANGELOG.md`, README status and any
tag remain unchanged in this pass — a separate closeout step, mirroring the
v2.1/v2.2 pattern. S4 (computational-kernel unification under
`kernel/computational`) is explicitly deferred; see ADR 0021's non-goals.

### v2.5 computational kernel unification rebuild

Rebuilt on **2026-07-27** after unifying root-finding, interpolation,
differentiation, integration, and ODE solving under
`src/oec/kernel/computational/` (ADR 0022) — the "computational"
prerequisite of the v2.5 "Mathematics Complete" hard gate, deferred from
v2.4 as S4 (ADR 0021). `kernel/numerics/{root_finding,root_system,ode}.py`
were deleted (logic moved, not duplicated); a new `mathematics.differentiate`
experimental skill was added (differentiation didn't exist anywhere before).
**8043 nodes**, **12019 edges**, **620 communities**. Package version,
`CHANGELOG.md`, README status and any tag remain unchanged — golden-set
expansion to 130 cases and the public-API documentation audit remain
separate, larger v2.5 slices not started here.

### Post-review Verification Engine correction rebuild

Rebuilt on **2026-07-27** after an independent review (fable) of the day's
work found the v2.4 Verification Engine's `lp_gap`/`reproducibility`
post-checks didn't do what their names claimed (ADR 0021 amendment), and
after rewriting the near-tautological Math IR LP parity test to go through
the real `optimization.lp` skill instead of duplicating
`compile_linear`'s own internals. **8061 nodes**, **12077 edges**, **669
communities** — this count also reflects an unrelated, uncommitted,
in-progress MCP specialist-agent router (`src/oec/mcp/server.py` and
friends) another concurrent session was actively editing in the same
working tree at rebuild time; that work is not part of this commit.

### v2.5.0 release closeout rebuild

Rebuilt on **2026-07-29** after the v2.4/v2.5 release metadata closeout
(version bump `2.3.0 → 2.5.0`, `CHANGELOG.md` v2.5.0 entry consolidating both
versions, README status, `skill-inventory.md` reconciled `40 → 63`,
`technical-debt.md` closures) plus the MCP natural-language scalar-extrema
routing feature (`agent.default` request-field domain inference,
`AppliedMathematicsSpecialist.run_request`) committed immediately before this
closeout. **8328 nodes**, **12547 edges**, **664 communities** — graph now
above the 5000-node visualization limit, so `graph.html` is the aggregated
community view; use `graph.json` + `GRAPH_REPORT.md` for node-level detail.
The closeout changes are committed as the v2.5.0 release commit immediately
after this rebuild.

### v2.5.1 refinement release rebuild

Rebuilt on **2026-07-30** after the v2.5.1 refinement release: the
AR/autocorrelation package (`src/oec/kernel/timeseries/ar.py` +
`timeseries.{autocorrelation,pacf,ar_yule_walker,levinson_durbin}`),
`agent.default` routing extension, four new kernel-level coverage-push
test files, and the release metadata closeout (version `2.5.0 → 2.5.1`,
`CHANGELOG.md`, README, `skill-inventory.md` `63 → 67`,
`technical-debt.md`). **8846 nodes**, **13210 edges**, **669
communities** — still above the 5000-node visualization limit;
`graph.html` remains the aggregated community view. The closeout changes
are committed as the v2.5.1 release commit immediately after this
rebuild.

### MCP agent-router runtime fix + free-text discovery fallback rebuild

Rebuilt on **2026-07-30** (tool now `graphifyy` v0.9.31, previously v0.9.28
— command surface unchanged) after a same-day session fixed a real,
host-reproduced runtime failure in the MCP agent-first layer and a
follow-on functional gap it surfaced. **8999 nodes, 13434 edges, 671
communities.** Baseline commit is still `f1c09c31` (the v2.5.1 release) —
everything below is **uncommitted** in the working tree at rebuild time,
mirroring the same pattern noted in the "Post-review Verification Engine
correction rebuild" entry above.

What changed, in the order it was found and fixed:

1. **`agent.*` MCP tools failed with `ModuleNotFoundError: No module named
   'agents'`** when the server was launched by a real MCP host runtime from
   a cwd other than the repo root (`agents/` is a PEP 420 namespace package
   outside `src/oec`, only importable when the repo root happens to be on
   `sys.path` — true under `pytest`, not guaranteed by any real launcher).
   Reproduced directly against a host's actual `uv.exe --directory … run
   --extra mcp --extra optimization oec server mcp` launch command before
   fixing. Fixed via `oec.mcp.server._ensure_agents_importable()`, which
   resolves the repo root from its own `__file__` at import time instead of
   relying on the caller's cwd/`PYTHONPATH`.
2. **`call_tool()` only caught `OECError`/`ValueError`/`TypeError`** around
   agent and raw-skill dispatch; anything else (like the `ModuleNotFoundError`
   above) fell through to the `mcp` SDK's own generic handler, which kept the
   session alive but dropped this codebase's structured `{"error", "details":
   {"tool", "error_type"}}` error shape in favor of unstructured plain text.
   `call_tool()` now catches unexpected exceptions on both dispatch paths,
   logs them, and returns the same structured shape as every other error.
3. **`oec server mcp`/`oec server api` silently started with zero skills**
   when `--skills-root`/`OEC_SKILLS_ROOT` pointed at a missing directory
   (`discover_skill_dirs` tolerates that by design, for one-shot commands
   like `skills list`) — every tool call then failed downstream with no
   indication the root itself was wrong. Both server commands now fail fast.
4. **`agent.default` — the documented default MCP entrypoint — was a dead
   end for free-text `request` in 4 of 5 domains.** The router correctly
   inferred a domain from natural language, but every specialist except
   `agent.applied_mathematics` (and that one only for a narrow scalar-extrema
   regex grammar) only accepted `demo_label` or `skill_id`+`inputs`, so the
   bare `request` was rejected with `ValueError` downstream. Confirmed for
   real via a 41-prompt Ollama-driven stress test against the live server
   (`nemotron-3-nano:4b-64k` picking its own tool calls — see
   `docs/implementation/OLLAMA_AGENT_STRESS_TEST_REPORT.md`): 4 of 5 real
   `agent.default` calls failed identically. Fixed with a new module,
   `src/oec/mcp/discovery.py` (`rank_candidate_skills`,
   `build_skill_suggestion_payload`): a specialist that can't act on
   `request` now returns a non-error `{"status": "needs_more_information",
   "candidates": [...]}` payload — each candidate carrying its real
   `input.schema.json` plus a worked example from the skill's `examples/`
   dir — instead of raising, wired into all four gap points in
   `_run_specialist_by_name`. Same pass also fixed
   `_infer_domain_from_request`'s bare substring matching (`"lp" in text`
   matched inside "he**lp**"; `"ops" in text` matched inside
   "sh**ops**"/"dr**ops**"), replaced with word-boundary-aware
   `_contains_token`.

All four points are covered by new tests (`tests/unit/test_mcp_discovery.py`,
several new cases in `tests/integration/test_mcp_server.py`, plus CLI
fail-fast tests in `tests/unit/test_cli.py`); full suite is green (1444
passed) and ruff/mypy are clean across `src/`+`tests/`. Two independent
reviews (Opus, Fable) ran against this work before and after implementation;
findings from both were folded back in (see `docs/implementation/
technical-debt.md` D-CUR-21/22/23 for what each fix actually closed and
what's still open — ranking-quality heuristic, orphan domains with no
specialist at all, and the structural `agents/` packaging follow-up).
Rebuild Graphify again once this lands as a commit.

### Post-audit router corrections rebuild

Rebuilt on **2026-07-30** (still later the same night) after implementing
the two corrections an independent audit found in the previous entry's
work (`docs/implementation/oec-agent-router-post-audit-corrections.md`).
**9043 nodes, 13507 edges, 702 communities.** Baseline commit is still
`f1c09c31` (the v2.5.1 release) — this, like the previous entry, is
**uncommitted** in the working tree at rebuild time. Distinguish this from
the v2.5.1 release baseline: nothing here has shipped yet.

1. **`_has_execution_payload()`** (`src/oec/mcp/server.py`) — the router
   used to treat bare *presence* of an `execution` key as a signal to route
   to `agent.scientific_reviewer`, so a local LLM hallucinating an empty
   `execution: {}` alongside a valid optimization request got diverted
   there and failed validation instead of running. The router now requires
   `execution` to actually carry `status`/`skill`/`method`/`started_at`
   before it counts as a review signal.
2. **`OptimizationSpecialist.run_skill()`** (`agents/optimization_
   specialist/specialist.py`) — the discovery fallback added in the
   previous entry told callers to retry with `skill_id`+`inputs`, but
   `agent.optimization_specialist` only accepted `ops`/`demo_label`, so the
   promised retry loop was a dead end. It now runs an explicit
   `optimization.*` skill directly via `Engine.run`.

Also fixed in the same pass, outside the router itself: two ruff findings
(`SIM105`, `SIM117`) and one mypy `no-any-return` in
`scripts/ollama_agent_stress_test.py`, plus a stale technical-debt claim
(D-CUR-21 said the broad `except Exception` handlers had no logging; they
do now, from the previous entry's own work — the doc just hadn't been
updated) and a UTC/local date mismatch in `OLLAMA_AGENT_STRESS_TEST_REPORT.md`'s
header. See `docs/implementation/technical-debt.md` (D-CUR-24, D-CUR-25)
for full detail and remaining scope (a live post-fix Ollama rerun was
kicked off alongside this work; check `OLLAMA_AGENT_STRESS_TEST_REPORT.md`'s
addendum for whether it landed and what it found).

### Discovery payload normalization rebuild

Rebuilt on **2026-07-30** after the final independent validation of the
post-audit router work. **9058 nodes, 13523 edges, 679 communities.** The
aggregated HTML graph contains 679 community nodes and 821 cross-community
edges. The code graph remains local and gitignored; this entry records the
working-tree evidence immediately before commit.

The optimization retry transport fix was correct but exposed a final contract
bug: `discovery._first_example()` returned whole human-readable example files
such as `{"description": "…", "input": {…}}`, whereas the documented
`example_inputs` contract says that object can be sent directly as `inputs`.
That produced an honest but unusable `ExecutionResult(status=INVALID)` because
the wrapper fields are not part of the skill schema. The function now unwraps
the nested object when present while preserving legacy flat examples.

This was verified with the exact user-facing loop, with no test-only
normalization:

`agent.default request → optimization candidate → candidate.example_inputs →
agent.default skill_id+inputs → agent.optimization_specialist → VALIDATED`.

Focused discovery/MCP tests passed (**78 passed**), Ruff and focused mypy
passed, and `git diff --check` was clean. The post-fix Ollama artifact remains
evidence of transport resilience; it did not happen to attempt this exact
retry leg, so deterministic end-to-end coverage is the acceptance evidence
for the payload contract.

### v2.5.2 confidence-routing rebuild

Rebuilt on **2026-07-30** while preparing the v2.5.2 commit. **9077 nodes,
13578 edges, 701 communities** (aggregated HTML: 701 community nodes and 933
cross-community edges). The prior committed baseline was `f68a951`; the
Graphify artifacts remain local and gitignored, while this entry records the
source-tree state that was validated for commit.

This rebuild covers the next `agent.default` reliability pass: deterministic
weighted domain intent ranking, structured `needs_clarification` for absent or
tied free-text intent, and new `agent.control_dynamics` plus
`agent.finance_uncertainty` specialists. Explicit operational signals still
outrank inference. Focused discovery/MCP coverage passed **84 tests**; the
final independent Fable review passed. The remaining D-CUR-23 work is not a
claim of semantic understanding: aliases and weights need a versioned golden
routing corpus and production-style telemetry before tuning.

Graphify could not enumerate `.pytest-tmp` due to a Windows access-denied
warning; that transient test directory is outside the committed source scope.

### v2.5.3 authoritative-answer hardening rebuild

Rebuilt on **2026-08-03** (tool now `graphifyy` v0.9.32, previously v0.9.31)
after the v2.5.3 Waves 1-5 work: `src/oec/mcp/envelope.py` (authoritative
answer envelope), `src/oec/mcp/divergence.py` (`claimed_answer` +
`host_output_diverged`), `scripts/_oec_authority.py` + updated
`hermes_supertest.py`/`multiagent_with_without_oec.py` harnesses,
`schemas/authoritative_answer.schema.json`, ADR 0023, and the release
metadata closeout (version bump `2.5.2 → 2.5.3`, `CHANGELOG.md`,
`technical-debt.md` D-CUR-26 closure + new D-CUR-27 residual entry).
**9587 nodes, 14346 edges, 730 communities** (aggregated HTML: 730
community nodes, 960 cross-community edges — still above the 5000-node
visualization limit). Baseline commit is still `129dcc0` (Wave 3b); this,
like several prior entries, is **uncommitted** in the working tree at
rebuild time. `graphify-out/` remains local and gitignored (ADR 0010).

## Known limitations observed

`GRAPH_REPORT.md` flagged 33 weakly-connected nodes (mostly Markdown
section headers from ADRs and issue templates, which is expected — prose
structure, not code structure) and 9 inferred (not extracted) edges around
`VersionedRef`, worth a second look once the loader/registry start
consuming these models in Sprint 01.
