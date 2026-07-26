# Skill inventory

**Updated:** 2026-07-26 (GPT plan remainder closed: S7′ + S10 + S19 + S23–S26)
**Registry root:** `skills/`

## Summary

| Domain | Count | Notes |
|---|---|---|
| mathematics | 6 | SciPy scalar methods |
| electrical | 6 | closed-form + Pint |
| timeseries | 9 | + timegrid, quality ops |
| linear | 2 | solve + matrix_properties |
| numerical | 2 | ode_ivp, root_system |
| statistics | 2 | describe + monte_carlo |
| optimization | 7 | lp, milp, feasibility, scenario, qp, nlp, multiobjective |
| energy | 2 | balance, load_metrics |
| battery | 1 | soc_step |
| finance | 3 | simple_returns, max_drawdown, var_historical |
| **Total** | **40** | experimental @ 0.1.0 |

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
