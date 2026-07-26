# OEC Agents (Phase G)

Optional layer **outside** the core `oec` wheel. Agents **formulate and
review**; they never invent numerical answers. Execution always goes
through OEC skills (`optimization.lp` / `optimization.milp`, etc.).

```text
LLM / user
    → Optimization Specialist  (OPS + classify + run)
    → OEC Skill Engine         (validate + HiGHS/SciPy)
    → Scientific Reviewer      (audit OPS + ExecutionResult)
```

| Agent | Path | Role |
|---|---|---|
| Optimization Specialist | `optimization_specialist/` | Build/validate OPS, execute LP/MILP, narrate from result only |
| Scientific Reviewer | `scientific_reviewer/` | Independent checklist on OPS + `ExecutionResult` |

## Install

```bash
uv sync --extra optimization   # HiGHS for LP/MILP
# agents/ is imported from the repo root (dev); not a separate package yet
```

```python
from agents.optimization_specialist.specialist import OptimizationSpecialist
from agents.scientific_reviewer.reviewer import ScientificReviewer
```

## Rules

1. **No silent method shopping** — method is the OEC skill + OPS.
2. **No invented numbers** — narrative cites only `ExecutionResult` fields.
3. **SciPy/HiGHS own numerical merit** — agents contribute workflow, not algorithms.
4. Private decision engines stay out of this tree (what/why/decision).
