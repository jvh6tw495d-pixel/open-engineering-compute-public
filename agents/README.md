# OEC Agents (Phase G + S20–S22)

Optional layer **outside** the core `oec` wheel. Agents **formulate and
review**; they never invent numerical answers. Execution always goes
through OEC skills.

```text
LLM / user
    → Specialist agents        (map problem → skill inputs / OPS)
    → OEC Skill Engine         (validate + SciPy/NumPy/pandas/HiGHS)
    → Scientific Reviewer      (audit OPS + ExecutionResult)
```

| Agent | Path | Role |
|---|---|---|
| Optimization Specialist | `optimization_specialist/` | Build/validate OPS, execute LP/MILP, narrate from result only |
| Scientific Reviewer | `scientific_reviewer/` | Independent checklist on OPS + `ExecutionResult` |
| Applied Mathematics | `applied_mathematics/` | Math / linear / stats / ODE skills via `SkillSpecialist` |
| Time-Series | `time_series/` | `timeseries.*` quality and grid ops |
| Energy | `energy/` | Public energy / battery / electrical skills only |
| Control & Dynamics | `control_dynamics/` | `control.*` / `dynamics.*` skills via `SkillSpecialist` |
| Finance & Uncertainty | `finance_uncertainty/` | `finance.*` / `uncertainty.*` skills via `SkillSpecialist` |

Shared harness: `agents/common.py` (`SkillSpecialist`, `narrate_execution`).

## Packaging

The `agents/` tree is a **dev-only companion layer kept outside the core
`oec` wheel** (per V3 plan §3, work package C4). It is **not** shipped on
PyPI and is **not** a separate installable package at v1.5. Code here
imports `oec` (the installed wheel) and is itself imported by tests and
harnesses that run from the **repository root**.

### Import path

Because `agents/` lives at the repo root (not under `src/oec/`), the
import `from agents.<specialist>...` only resolves when the **repository
root** is on `sys.path`. In practice:

- `pytest`, `ruff`, `mypy` invoked from the repo root already add it.
- For ad-hoc scripts / REPLs, export `PYTHONPATH` to the repo root:

```bash
# POSIX
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Windows PowerShell
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
```

Alternatively run Python from the repo root without modifying
`PYTHONPATH` (the current working directory is prepended to `sys.path`).

`oec.mcp.server` (the MCP `agent.*` tools) does this automatically: it
resolves the repo root from its own file location and appends it to
`sys.path` at import time, so a host launching the MCP server from any cwd
still gets a working `agents/` import. That is a runtime patch, not a
packaging fix — see `docs/implementation/technical-debt.md` (D-CUR-21) for
the open follow-up to make `agents/` importable without any `sys.path`
patching.

## Install

```bash
uv sync --extra optimization   # HiGHS for LP/MILP
# agents/ is imported from the repo root (dev); not a separate package yet
```

```python
from agents.optimization_specialist.specialist import OptimizationSpecialist
from agents.scientific_reviewer.reviewer import ScientificReviewer
from agents.applied_mathematics.specialist import AppliedMathematicsSpecialist
from agents.time_series.specialist import TimeSeriesSpecialist
from agents.energy.specialist import EnergySpecialist
```

## Rules

1. **No silent method shopping** — method is the OEC skill (+ OPS when applicable).
2. **No invented numbers** — narrative cites only `ExecutionResult` fields.
3. **SciPy/HiGHS/pandas own numerical merit** — agents contribute workflow, not algorithms.
4. Private decision engines stay out of this tree (what/why/decision).
