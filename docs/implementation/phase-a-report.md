# Phase A report — core consolidation

**Status:** GO for Phase B/C
**Date:** 2026-07-26

## Delivered

| Sub-phase | Outcome |
|---|---|
| A0 | Baseline inventory, debt list, SciPy-governance positioning |
| A1 | ExecutionResult contract docs; `input_hash` + `backends[]` (ADR 0017) |
| A2 | Input limits; units/reproducibility/sandbox honesty docs |
| A3 | Multi-skill contract test (12 skills); ADR 0005 electrical surface |

## Gate

- pytest green on Phase A changes (full suite run at end of A–C)
- Contracts under `docs/contracts/`
- No private-system nomenclature in public tree

## Explicitly not done in A (by design)

- OS-level network/FS/memory isolation
- Auto-fill of `assumptions`/`conventions` from skill.md
- OPS / LP / MILP / HiGHS (Phase B/C)
- Specialist agents (Phase G)

## GO / NO-GO

**GO** → proceed to backends (HiGHS) and OPS/LP/MILP.

---

## Phases B–C (executed after A3)

| Phase | Delivered |
|---|---|
| B | `highspy` optional extra; `oec.kernel.optimization.highs` adapter; provenance lists highspy when installed |
| C | OPS v0.1 (`oec.ops`), skills `optimization.lp` / `optimization.milp`, feasibility messages on infeasible/bound conflicts |
