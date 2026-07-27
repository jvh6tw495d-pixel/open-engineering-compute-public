# Technical debt

**Current-state review:** 2026-07-27 at `oec==2.0.0`.

This file began as a Phase A snapshot. Historical entries remain for
traceability; the current queue below is the canonical starting point for new
work. An item is not closed merely because a later roadmap mentions it.

## Current queue

| ID | Priority | Item | Target / evidence |
|---|---|---|---|
| D-CUR-02 | P1 | Default five-second skill timeout can be consumed by a cold SciPy import on Windows | Measure and decide import/warmup versus timeout policy before public distribution |
| D-CUR-05 | P1 | No automated bare-physical-float authoring gate | v2.1 Q2; see `v2.1-quantities-q0-inventory.md` |
| D-CUR-06 | P1 | Energy and battery schemas carry physical values as bare numbers | v2.1 migration |
| D-CUR-07 | P1 | `diagnostics_from_mapping` heuristic coverage is thin | Core hardening |
| D-CUR-08 | P1 | `ProvenanceRecord` permits untyped extra passthrough | Core hardening without breaking ExecutionResult |
| D-CUR-09 | P1 | No OS-level memory/network/filesystem isolation | Pre-untrusted deployment; ADR 0012 |
| D-CUR-10 | P1 | REST/MCP have no authentication or rate limiting | Pre-untrusted deployment |
| D-CUR-11 | P2 | `SkillLifecycle.validate_transition` is unused at runtime | Lifecycle hardening |
| D-CUR-12 | P2 | Runner subprocess paths have limited direct coverage instrumentation | Test architecture |
| D-CUR-13 | P2 | Development telemetry/cost per accepted task is not implemented | Operations roadmap |
| D-CUR-14 | P2 | No formal Backend Registry or VerificationReport pipeline | v2.4 |
| D-CUR-15 | P2 | No Git tags or remote; “release” currently means private commit milestone | Explicit release-governance decision |

## Recently closed

| ID | Closed | Evidence |
|---|---|---|
| D-CUR-01 | 2026-07-27 | core independence probe now runs in a fresh interpreter; full suite 810 passed |
| D-CUR-03 | 2026-07-27 | V3 gap map reconciled with shipped `oec.core` and `ScientificResult` |
| D-CUR-04 | 2026-07-27 | Graphify rebuilt from `6e271496` before work; rebuild again at handoff |
| D-CUR-16 | 2026-07-27 | installation smoke now retains complete child stdout/stderr and separately proves installed CLI/sandbox and numerical backend execution |

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
