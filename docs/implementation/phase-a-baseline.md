# Phase A baseline

**Tag intent:** `baseline-phase-a` (optional after A0 commits)
**Date:** 2026-07-25
**Branch:** `main`
**Remotes:** none (private incubation)

## Already on `main` before A0 doc commits

| Area | Evidence (approx.) |
|---|---|
| Electrical skills (6) | commit `064967f` |
| Odysseus + Open Science | commit `e3f3026` |
| Public Alpha prep / community docs | commit `51c7b5e` |
| Dimensional normalization ADR 0016 | commit `4148c41` |
| Math skills (6) + SDK/CLI/REST/MCP | earlier sprints 00–07 |

## Runtime / deps (measured)

| Package | Version |
|---|---|
| Python | 3.12+ (project requires) |
| NumPy | 2.5.1 |
| SciPy | 1.18.0 |
| SymPy | 1.14.0 |
| Pint | 0.25.3 |
| pandas | not installed |
| HiGHS | not installed |

## Interfaces

| Surface | Status |
|---|---|
| Python SDK (`oec.sdk`) | OK |
| CLI (`oec`) | OK |
| REST (`/v1`) | OK |
| MCP (stdio) | OK |
| ADR 0005 four-interface conformance | OK for math sample; Phase A3 adds electrical sample |

## Execution pipeline

| Capability | Status | Phase A action |
|---|---|---|
| Skill load/registry/lifecycle models | OK | document |
| Graded `ExecutionStatus` (ADR 0007) | OK | **do not replace with `success`** |
| Pint + central normalization (ADR 0016) | OK | doc + regression tests |
| Subprocess sandbox + timeout (ADR 0012) | OK partial | doc honesty: no OS mem/net/fs jail |
| Provenance | partial | A1: `input_hash`, `backends` |
| Payload/array size limits | weak/absent | A2 |
| Expression AST whitelist | OK (numerics) | A2 security test |

## Gate snapshot (A0)

Measured 2026-07-26:

```text
uv run pytest -q
  → 696 passed, 3 deselected, coverage 96.27%

uv run python scripts/check_forbidden_names.py
  → ok: scanned 333 files, zero forbidden terms

git remote -v
  → (empty — incubation)
```

## A0 remaining uncommitted at start of this note

- `README.md` / `CONTRIBUTING.md` (SciPy governance positioning)
- `docs/concepts/mathematical-engine-and-governance.md`
- `docs/implementation/OEC_IMPLEMENTATION_PLAN.md`
- this baseline / inventory / debt set

These are committed as part of A0 closure.
