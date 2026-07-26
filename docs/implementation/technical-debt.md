# Technical debt (Phase A view)

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
