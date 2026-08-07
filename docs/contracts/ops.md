# OEC Problem Specification (OPS) v0.1

**Phase C.** Structured language for linear / mixed-integer programs.
No arbitrary Python.

## Shape (summary)

```json
{
  "ops_version": "0.1.0",
  "problem_class": "lp | milp",
  "sense": "min | max",
  "variables": [{ "name": "x", "kind": "continuous|integer|binary", "lower": 0, "upper": null }],
  "constraints": [{ "name": "c1", "coeffs": { "x": 1 }, "sense": "<=|>=|=", "rhs": 0 }],
  "objective": { "coeffs": { "x": 1 }, "offset": 0 },
  "assumptions": [],
  "execution_limits": { "time_limit_seconds": 30 }
}
```

## Skills

| Skill | OPS class |
|---|---|
| `optimization.lp` | `lp` (all continuous) |
| `optimization.milp` | `milp` (≥1 integer/binary) |

## Backend

HiGHS via `highspy` (`uv sync --extra optimization`). Algorithmic merit: HiGHS.

## Validation

`oec.ops.models.validate_ops` — JSON Schema + semantic checks (unknown vars,
bound inversion, lp/milp consistency).
