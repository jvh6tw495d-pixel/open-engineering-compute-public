# Skill inventory

**Updated:** 2026-07-29 (v2.5 release closeout — reconciled against the real
`skills/` tree; the count below had drifted from 40 as v2.2–v2.5 work landed
without an inventory refresh)
**Registry root:** `skills/`

## Summary

| Domain | Count | Notes |
|---|---|---|
| mathematics | 8 | + `differentiate`, `solve_ir` (Math IR) since v2.2/v2.5 |
| electrical | 6 | closed-form + Pint |
| timeseries | 12 | + `align`, `backtest`, `forecast_simple`, `lag_features`, `power_to_energy` since v2.3 |
| linear | 5 | + `eig`, `least_squares`, `residual_norms` since v2.3 |
| numerical | 2 | ode_ivp, root_system |
| statistics | 5 | + `bootstrap`, `intervals`, `regression` since v2.3 |
| optimization | 12 | + `cvar_lp`, `infeasibility_explain`, `lp_diagnostics`, `pareto_lp`, `robust_lp` since v2.3 |
| energy | 2 | balance, load_metrics |
| battery | 1 | soc_step |
| finance | 3 | simple_returns, max_drawdown, var_historical |
| control | 2 | `kalman_filter`, `pid_discrete` (v2.3 Wave B) |
| dynamics | 2 | `stability_margins`, `state_space_simulate` (v2.3 Wave B) |
| uncertainty | 3 | `lhs`, `morris`, `propagate_linear` (v2.3 Wave B) |
| **Total** | **63** | experimental @ 0.1.0–0.2.0 (see each skill's `skill.yaml`) |

## GPT plan coverage

| Sprint / Fase | Skills / deliverables |
|---|---|
| S5′–S6′ | `optimization.lp`, `optimization.milp` |
| S7′ | `optimization.check_feasibility`, `optimization.scenario_batch` |
| S8′–S9′ | agents Optimization Specialist, Scientific Reviewer |
| S10–S12 | timeseries.* including `timegrid` |
| S13–S15 | linear.*, numerical.*, statistics.* |
| S16–S18 | energy.*, battery.soc_step |
| S19 | finance.* |
| S20–S22 | Math / Time-Series / Energy agents |
| S23–S26 | `optimization.qp`, `optimization.nlp`, `optimization.multiobjective` |

## How to call

| Interface | Entry |
|---|---|
| SDK | `oec.sdk.Engine(skills_root=...).run(skill_id, inputs)` |
| CLI | `oec run <skill_id> --input '...' --skills-root skills` |
| REST | `POST /v1/skills/{skill_id}/run` |
| MCP | tool name = skill id |

## Notes

- Numerical merit: SciPy / NumPy / pandas / HiGHS. OEC governs contracts.
- Agents never invent numbers.
- Private dispatch / commercial scoring out of public tree.
