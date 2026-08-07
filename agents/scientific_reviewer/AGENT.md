# Scientific Reviewer v0.1

## Role

Independent audit of an **OPS** document and an **ExecutionResult**.
Does not re-solve the model. Does not invent numbers.

## Checks

| Code | Check |
|---|---|
| `ops_valid` | OPS validates under v0.1 rules |
| `class_skill_match` | skill_id matches problem_class (lp/milp) |
| `bounds_consistent` | no lower > upper |
| `objective_vars_known` | objective coeffs ⊆ variables |
| `constraint_vars_known` | constraint coeffs ⊆ variables |
| `status_solver_consistency` | OEC status vs `result.solver_status` |
| `no_false_optimal` | non-optimal solver not claimed as VERIFIED success without caveats |
| `feasibility_on_infeasible` | infeasible has issues list or diagnostics |
| `provenance_present` | run_id, input_hash present |
| `assumptions_present` | warning if OPS assumptions empty |
| `claimed_numbers` | optional claimed_* fields must match result |

## Success criteria

Deliberately broken OPS or forged results are flagged `failed` with
actionable check codes.
