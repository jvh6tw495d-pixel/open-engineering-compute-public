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

Shared harness: `agents/common.py` (`SkillSpecialist`, `narrate_execution`).

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
