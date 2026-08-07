# ADR 0018: Roadmap sequencing (Alpha freeze) and pandas as core

- **Status:** accepted
- **Date:** 2026-07-26
- **Context:** Opus review of GPT plan completion (findings F1, F3)

## Context

The implementation plan (`docs/implementation/OEC_IMPLEMENTATION_PLAN.md`)
originally required:

1. Finish Alpha S0′–S9′;
2. **STOP** and freeze domain expansion until agent metrics were green;
3. Only then open Roadmap B (S10–S26).

In practice, Phases D–G and catalog expansions (time series, energy, finance,
advanced optimization skills, extra specialists) landed in the same incubation
tree before a formal Public Alpha tree existed. Separately, `pandas` was added
as a **core** dependency because timeseries skills are first-class in the
public catalog.

Opus review flagged both as process/documentation debt, not missing features.

## Decision

### 1. Sequencing (ratify, do not revert code)

We **accept** that Roadmap B was delivered on the incubation `main` branch
before the Public Alpha *release procedure* (`docs/release/public-alpha.md`)
was executed. Rationale:

- Skills and agents remain **public-generic** (ADR 0008 filter still holds).
- Numerical merit stays with SciPy/NumPy/pandas/HiGHS; agents still do not invent numbers.
- Reverting B would destroy working, tested value without improving governance.

**Going forward:**

- New *private* methodology stays out of this tree (ADR 0008).
- Public Alpha means a **new git history / sibling tree** via
  `scripts/prepare_public_alpha.py`, not a rollback of B.
- Agent metrics harness (`benchmarks/agent_metrics.py`) is required as a
  **gate signal**, not as a reason to delete B skills.

### 2. pandas is a core dependency

`pandas>=3.0.5` remains in `[project].dependencies` (not only an extra).

Reasons:

- Multiple first-class skills (`timeseries.*`) and kernels import pandas.
- Optional-extra installs that omit pandas would leave half the catalog unloadable.
- NumPy/SciPy already set a scientific-stack floor; pandas is consistent with that floor for grid/series work.

Optional extras remain for **heavy / optional interfaces only**:

- `optimization` → HiGHS (`highspy`)
- `api` → FastAPI/uvicorn
- `mcp` → MCP server

If a future ultra-minimal wheel is required, that is a **new product packaging
decision**, not a silent removal of pandas from the default install.

## Consequences

- Plan document DoD checkboxes marked complete; §1.2 audit table updated.
- No code rollback of Roadmap B.
- Metrics harness must stay green in CI/dev for agent claims.
- Reviewers should treat “Alpha freeze” as a **release process** gate, not as
  “B skills must not exist yet.”
