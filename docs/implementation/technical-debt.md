# Technical debt

**Current-state review:** 2026-07-28 at `oec==2.3.0` (package metadata still
unbumped past 2.3.0 despite v2.4/v2.5 kernel-unification, verification, and
golden-set work already committed on `codex/oec-v2.5` — see
`docs/implementation/v2.1-delivery-status-and-v2.5-next-steps.md` for the
metadata/version-bump backlog this predates).

This file began as a Phase A snapshot. Historical entries remain for
traceability; the current queue below is the canonical starting point for new
work. An item is not closed merely because a later roadmap mentions it — each
closure below cites the commit/file that actually did it.

## Current queue

| ID | Priority | Item | Target / evidence |
|---|---|---|---|
| D-CUR-02 | P1 | Default five-second skill timeout can be consumed by a cold SciPy import on Windows | Still open — measure and decide import/warmup versus timeout policy before public distribution |
| D-CUR-07 | P1 | `diagnostics_from_mapping` (`src/oec/core/diagnostics.py`) heuristic coverage is thin | Still open — core hardening |
| D-CUR-08 | P1 | `oec.core.provenance.ProvenanceRecord` permits untyped extra passthrough (`extra="allow"`) | Still open by design (ADR 0017); revisit only if it starts hiding real schema drift |
| D-CUR-09 | P1 | No OS-level memory/network/filesystem isolation | Still open — pre-untrusted deployment; ADR 0012 |
| D-CUR-10 | P1 | REST/MCP have no authentication or rate limiting | Still open — confirmed current in `docs/api/README.md` and `docs/mcp/README.md`'s own "not yet implemented" sections |
| D-CUR-11 | P2 | `SkillLifecycle.validate_transition` (`src/oec/skills/lifecycle/lifecycle.py`) is unused outside its own test | Still open — confirmed via repo-wide reference search |
| D-CUR-12 | P2 | Runner subprocess paths have limited direct coverage instrumentation | Still open — `src/oec/execution/runner.py` at 73% (crash/timeout branches uncovered) |
| D-CUR-13 | P2 | Development telemetry/cost per accepted task is not implemented | Still open — operations roadmap |
| D-CUR-15 | P2 | No Git tags or remote; “release” currently means private commit milestone | Still open — explicit release-governance decision |
| D-CUR-19 | P2 | `src/oec/kernel/` package coverage is 86%, below the 90% critical-path bar the rest of the package list clears | 11 submodules ranked weakest-first in `docs/implementation/v2.5-critical-path-coverage.md` §3 |

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
