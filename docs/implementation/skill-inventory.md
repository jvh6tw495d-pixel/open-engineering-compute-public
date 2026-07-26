# Skill inventory (Phase A baseline)

**Generated for:** Phase A0
**Date:** 2026-07-25
**Registry root:** `skills/`
**IDs:** real package IDs (`mathematics.*`, `electrical.*`) — not `math.*`

## Summary

| Domain | Count | Status |
|---|---|---|
| mathematics | 6 | experimental @ 0.1.0 |
| electrical | 6 | experimental @ 0.1.0 |
| **Total** | **12** | all loadable |

## Mathematics

| Skill ID | Version | Method ID | Iterative | Effective backend | Package tests | Integration e2e |
|---|---|---|---|---|---|---|
| `mathematics.solve_root` | 0.1.0 | `scalar_root_finding` | yes | SciPy (`brentq`/`bisect`/`secant`/`newton`) + AST expressions | golden, properties, validation | `test_solve_root_end_to_end.py` |
| `mathematics.interpolate` | 0.1.0 | `scalar_interpolation` | no | NumPy / SciPy interpolate | golden, properties, validation | `test_interpolate_end_to_end.py` |
| `mathematics.integrate` | 0.1.0 | `scalar_integration` | yes* | SciPy `quad` / NumPy trapz-simpson path | golden, properties, validation | `test_integrate_end_to_end.py` |
| `mathematics.optimize_scalar` | 0.1.0 | `scalar_minimization` | yes | SciPy `minimize_scalar` | golden, properties, validation | `test_optimize_scalar_end_to_end.py` |
| `mathematics.optimize_constrained` | 0.1.0 | `constrained_minimization` | yes | SciPy `minimize` (SLSQP / trust-constr) | golden, properties, validation | `test_optimize_constrained_end_to_end.py` |
| `mathematics.curve_fit` | 0.1.0 | `nonlinear_least_squares` | yes | SciPy `curve_fit` | golden, properties, validation | `test_curve_fit_end_to_end.py` |

\*Function mode is adaptive; tabulated mode is closed-form but manifest declares iterative at skill level.

## Electrical

| Skill ID | Version | Method ID | Iterative | Effective backend | Package tests | Integration e2e |
|---|---|---|---|---|---|---|
| `electrical.three_phase_power` | 0.1.0 | `balanced_three_phase_power` | no | Closed-form (+ Pint normalize) | golden, properties, validation | `test_three_phase_power_end_to_end.py` |
| `electrical.current_from_power` | 0.1.0 | `current_from_power` | no | Closed-form (+ Pint) | golden, properties, validation | `test_current_from_power_end_to_end.py` |
| `electrical.voltage_drop` | 0.1.0 | `conductor_voltage_drop` | no | Closed-form (+ Pint) | golden, properties, validation | `test_voltage_drop_end_to_end.py` |
| `electrical.power_factor_correction` | 0.1.0 | `capacitor_bank_sizing` | no | Closed-form (+ Pint) | golden, properties, validation | `test_power_factor_correction_end_to_end.py` |
| `electrical.transformer_loading` | 0.1.0 | `apparent_power_loading` | no | Closed-form (+ Pint) | golden, properties, validation | `test_transformer_loading_end_to_end.py` |
| `electrical.per_unit_conversion` | 0.1.0 | `classical_per_unit` | no | Closed-form (+ Pint) | golden, properties, validation | `test_per_unit_conversion_end_to_end.py` |

## How to call (all skills)

| Interface | Entry |
|---|---|
| SDK | `oec.sdk.Engine(skills_root=...).run(skill_id, inputs)` |
| CLI | `oec run <skill_id> --input '...' --skills-root skills` |
| REST | `POST /v1/skills/{skill_id}/run` |
| MCP | tool name = skill id; plus `list_skills` |

## Notes for Phase A

- Merit of numerical methods: **SciPy/NumPy** (math skills). OEC governs contracts.
- Electrical skills: classical identities; units via **Pint** / ADR 0016.
- No LP/MILP/HiGHS skills yet (post–Phase A).
- Provenance today: `oec_version`, `git_commit`, `trace_id`, sandbox flags, optional `units` — **missing** `input_hash` and explicit `backends[]` (Phase A1).
