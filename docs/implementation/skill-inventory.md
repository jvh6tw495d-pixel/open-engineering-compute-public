# Skill inventory

**Updated:** 2026-07-26 (priorities 1–2 / S11–S15 + agents S20–S22)
**Registry root:** `skills/`

## Summary

| Domain | Count | Notes |
|---|---|---|
| mathematics | 6 | SciPy scalar methods |
| electrical | 6 | closed-form + Pint |
| timeseries | 8 | + detect_outliers, clip, normalize, rolling |
| linear | 2 | solve_system + matrix_properties |
| numerical | 2 | ode_ivp, root_system |
| statistics | 2 | describe + monte_carlo |
| optimization | 2 | LP / MILP via HiGHS |
| energy | 2 | balance, load_metrics |
| battery | 1 | soc_step (generic coulomb counting) |
| **Total** | **31** | experimental @ 0.1.0 |

## New in priorities 1–2

| Skill ID | Method | Backend merit |
|---|---|---|
| `timeseries.detect_outliers` | z-score / IQR | NumPy + pandas |
| `timeseries.clip` | clip bounds | pandas |
| `timeseries.normalize` | minmax / zscore | NumPy |
| `timeseries.rolling` | rolling agg | pandas |
| `linear.matrix_properties` | rank/cond/eig/SVD | NumPy linalg |
| `statistics.monte_carlo` | sample mean E[f(X)] | NumPy RNG + AST |

## Agents (outside core wheel)

| Agent | Sprint | Harness |
|---|---|---|
| Optimization Specialist | G / S8′ | OPS → `optimization.*` |
| Scientific Reviewer | G / S9′ | audit OPS + ExecutionResult |
| Applied Mathematics | S20 | `SkillSpecialist` demos |
| Time-Series | S21 | `SkillSpecialist` demos |
| Energy | S22 | public energy skills only |

## How to call

| Interface | Entry |
|---|---|
| SDK | `oec.sdk.Engine(skills_root=...).run(skill_id, inputs)` |
| CLI | `oec run <skill_id> --input '...' --skills-root skills` |
| REST | `POST /v1/skills/{skill_id}/run` |
| MCP | tool name = skill id; plus `list_skills` |

## Notes

- Merit of numerical methods: **SciPy / NumPy / pandas / HiGHS**. OEC governs contracts.
- Agents never invent numbers; narrative uses only `ExecutionResult`.
- Private dispatch / commercial BTM methodology stays out of public skills.
