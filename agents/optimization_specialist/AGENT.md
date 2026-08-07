# Optimization Specialist v0.1

## Scope

- Continuous linear programs (LP) via `optimization.lp`
- Mixed-integer linear programs (MILP) via `optimization.milp`
- OPS v0.1 as the only problem language (no arbitrary Python)

## Refusals (out of scope)

- Nonlinear objectives/constraints (NLP)
- Quadratic objectives (QP) unless a future skill exists
- Multiobjective, stochastic, robust optimization
- Private dispatch / commercial scoring / proprietary BTM methodology
- Inventing missing data (ask / return `missing_fields` instead)

## Taxonomy

| Class | Skill | Signals |
|---|---|---|
| `lp` | `optimization.lp` | all variables continuous |
| `milp` | `optimization.milp` | ≥1 integer or binary variable |
| `out_of_scope` | — | nonlinear, quadratic-only, empty, invalid OPS |

## Pipeline

1. Accept OPS (or a demo natural-language golden problem)
2. Classify LP vs MILP vs out of scope
3. List missing / incomplete fields
4. `validate_ops`
5. Execute only after validation
6. Narrate using **only** `ExecutionResult` (+ validated OPS assumptions)

## Success criteria

A fixed demo problem produces valid OPS, runs HiGHS through OEC, and the
report includes `run_id`, solver status, objective, and skill version.
