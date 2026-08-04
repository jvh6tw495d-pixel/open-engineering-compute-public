# Skill inventory

**Updated:** 2026-08-03 (v2.6 Wave 4 — Physics Foundation P1–P5 skills thin)
**Registry root:** `skills/`

## Summary

| Domain | Count | Notes |
|---|---|---|
| mathematics | 8 | + `differentiate`, `solve_ir` (Math IR) since v2.2/v2.5 |
| electrical | **7** | classic closed-form ×6 + **`dc_power_flow`** (P1 meshed DC, v2.6) |
| timeseries | 16 | + `autocorrelation`, `pacf`, `ar_yule_walker`, `levinson_durbin` since v2.5.1 |
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
| **thermal** | **1** | **`conduction_1d`** (P2 Fourier, v2.6) |
| **mechanics** | **1** | **`energy_1d`** (P3 KE/PE balance, v2.6) |
| **fluids** | **1** | **`bernoulli`** (P4 Bernoulli + Darcy-Weisbach f-input, v2.6) |
| **materials** | **1** | **`linear_constitutive`** (P5 Hooke + table lookup, v2.6) |
| **Total** | **72** | experimental @ 0.1.0–0.2.0 (see each skill's `skill.yaml`) |

## Physics Foundation P1–P5 (v2.6 Wave 4)

Thin adapters over `oec.physics.*` — zero inline physics arithmetic in
`implementation.py`. Gate V3: ≥1 skill per slice P1–P4; P5 skill preferred.

| Slice | Skill id | Physics module | AA kind (schema 1.1) |
|---|---|---|---|
| P1 | `electrical.dc_power_flow` | `oec.physics.electrical` | `energy_result` (electrical.* unchanged) |
| P2 | `thermal.conduction_1d` | `oec.physics.thermal` | `physics_result` |
| P3 | `mechanics.energy_1d` | `oec.physics.mechanics` | `physics_result` |
| P4 | `fluids.bernoulli` | `oec.physics.fluids` | `physics_result` |
| P5 | `materials.linear_constitutive` | `oec.physics.materials` | `physics_result` |

THD skill (`electrical.harmonics_thd`) is **optional** (D7) and not required
for the Wave 4 gate.

## How to call

| Interface | Entry |
|---|---|
| SDK | `oec.sdk.Engine(skills_root=...).run(skill_id, inputs)` |
| CLI | `oec run <skill_id> --input '...' --skills-root skills` |
| REST | `POST /v1/skills/{skill_id}/run` |
| MCP raw skill | tool name = skill id |
| MCP agent (electrical P1) | `agent.energy` / `agent.default` with `demo_label: "dc_power_flow"` or `skill_id` + `inputs` |
| MCP agent (thermal/mechanics/fluids/materials) | `skill_id` + `inputs` via `agent.default` (prefix routes to the catch-all specialist) or raw skill tool — **no new `agent.*` tools** |

### Agent demos (Energy Specialist)

| `demo_label` | Skill |
|---|---|
| `balance` | `energy.balance` |
| `load_metrics` | `energy.load_metrics` |
| `soc_step` | `battery.soc_step` |
| `power_to_energy` | `timeseries.power_to_energy` |
| `three_phase` | `electrical.three_phase_power` |
| **`dc_power_flow`** | **`electrical.dc_power_flow`** (Wave 4) |

Multi-domain physics demos beyond electrical are **docs/example-driven**
(see each skill's `examples/`); Wave 4 deliberately does not add four new
domain agents (tool-count gate).

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
| **v2.6 W4** | **P1–P5 physics skills + AA schema 1.1 `physics_result`** |

## Notes

- Numerical merit: SciPy / NumPy / pandas / HiGHS. OEC governs contracts.
- Agents never invent numbers.
- Private dispatch / commercial scoring out of public tree.
- Physics laws live in `src/oec/physics/`; skills only validate/adapt and call.
- Authoritative-answer kinds: see `docs/mcp/README.md` (schema **1.1**).
