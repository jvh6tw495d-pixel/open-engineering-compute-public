# Skill inventory

**Updated:** 2026-08-14 (3.6 S0–S5 implemented; S6 release gate pending)
**Registry root:** `skills/`
**Live load:** **151** skills across **28** domains, **0** contract-audit errors

## Summary

| Domain | Count | Notes |
|---|---|---|
| mathematics | 9 | + `jacobian` (W1) |
| electrical | 8 | classic + `dc_power_flow` + `harmonics_thd` |
| timeseries | 16 | AR/PACF package |
| linear | 5 | |
| numerical | 3 | + `pde_1d_heat` (W1) |
| statistics | 7 | + `distribution_eval`, `hypothesis_test` (W1) |
| optimization | 12 | HiGHS-backed subset needs `oec[optimization]` |
| energy | 7 | |
| battery | 2 | |
| finance | 3 | |
| control | 2 | |
| dynamics | 2 | |
| uncertainty | 3 | |
| thermal | 1 | |
| mechanics | 2 | + kinematics_1d (W3) |
| fluids | 1 | |
| materials | 1 | |
| chemistry | 8 | + vanthoff, hess_enthalpy (W3) |
| waves / optics / em / statistical_physics | 6 | W3 foundations |
| multiphysics | 2 | |
| **neural** | **26** | ADR 0031/0032 + **0033 training/search** |
| **evolutionary** | **15** | pymoo/DEAP/Nevergrad |
| **hybrid** | **2** | X2 surrogate + hyperparams |
| **scientific** | **1** | X3 method_select |
| foundation | 6 | W6/S1 + S5 embed / generate / capabilities / PEFT / vision / VLM |
| **Total** | **151** | all `experimental` in this inventory |

## W1-MVP scientific core (no AI)

| Skill id | Notes |
|----------|-------|
| `statistics.distribution_eval` | SciPy pdf/cdf/ppf/mean/std/sample |
| `statistics.hypothesis_test` | t_one/t_two/ks_1samp/mannwhitney |
| `mathematics.jacobian` | multi-var FD Jacobian |
| `numerical.pde_1d_heat` | 1D FDM heat/Poisson foundation |

## W3-MVP applied sciences foundations

| Skill id | Notes |
|----------|-------|
| `waves.phase_speed` | v = f λ + period/ω/k |
| `optics.snell` / `optics.thin_lens` | geometrical optics |
| `em.coulomb` / `em.parallel_plate_capacitor` | vacuum electrostatics |
| `statistical_physics.ideal_gas` | PV = nRT (+ optional v_rms) |
| `mechanics.kinematics_1d` | uniform acceleration |
| `chemistry.vanthoff` / `chemistry.hess_enthalpy` | thermochemistry |
| Experiments | `experiments/w3_*.json` |

## W4/W5 experiment builders (no new skills)

| Builder | Module | Maps to | MCP catalog (S4) |
|---------|--------|---------|------------------|
| `build_mlp_regressor_experiment` | `oec.experiment.neural` | `neural.mlp.regressor` | no (helper / S3 neural path) |
| `build_neural_training_mode_experiment` | `oec.experiment.neural` | `neural.training.*` | no (mode factory) |
| `build_optimize_single_experiment` | `oec.experiment.evolutionary` | `evolutionary.optimize_single` | **yes** |
| `build_nsga2_experiment` | `oec.experiment.evolutionary` | `evolutionary.nsga2` | **yes** |
| `build_hybrid_training_experiment` | `oec.experiment.evolutionary` | `neural.training.hybrid` | **yes** |
| `build_evo_sphere_experiment` | `oec.experiment.cross_domain` | sphere optimize gate | **yes** (W7) |

S4 industrial closure: the three public declarative evolutionary/hybrid builders
above are on the fail-closed cross-domain catalog
(`experiment.list_builders` / `experiment.run`). Helpers
(`sphere_problem_2d`, `problem_to_optimize_inputs`) stay uncatalogued.

See ADR 0037 · `docs/contracts/neural-evolutionary-experiments.md`.
**Excluded from 3.6 DoD:** NEAT / HyperNEAT (ADR 0042 — not deferred silently).

**3.6 closeout state:** S0–S5 are implemented; S6 is release CI/evidence and has not
created a tag, remote push, or published package. See
[`docs/release/3.6.0-CLOSEOUT.md`](../release/3.6.0-CLOSEOUT.md).

## Neural (3.4 + ADR 0033)

| Skill id | Wave |
|----------|------|
| `neural.mlp.regressor` / `classifier` / `predict` / `evaluate` | N1 |
| `neural.autoencoder.basic` / `denoising` | N2 |
| `neural.cnn1d` / `lstm` / `gru` / `tcn` | N3 |
| `neural.transformer.encoder` / `sequence_regressor` / `sequence_classifier` | N4 |
| `neural.gcn` / `graphsage` / `gat` | N5 (pure torch) |
| `neural.training.supervised` / `gradient` / `hybrid` / `neuroevolution` | ADR 0033 W1–W4 |
| `neural.search.hyperparameters` / `architecture` / `features` / `loss_weights` / `policy` | ADR 0033 W2–W6 |
| `neural.benchmark.training_strategy` | ADR 0033 W5 |

## Evolutionary (3.4)

| Skill id | Wave |
|----------|------|
| `optimize_single`, DE, GA, CMA-ES, PSO | E1 |
| `nsga2`, `nsga3`, `moead`, `pareto_search` | E2 |
| `benchmark` | X1 thin |
| `genetic_programming`, `evolution_strategy`, `custom_ga` | E3 |
| `blackbox_optimize`, `optimizer_portfolio` | E4 |

## Hybrid / Scientific (3.4)

| Skill id | Wave |
|----------|------|
| `hybrid.surrogate_optimize` | X2 |
| `hybrid.evo_hyperparams` | X2 |
| `scientific.method_select` | X3 |

## Physics Foundation P1–P5 (unchanged from 3.3)

| Slice | Skill |
|-------|--------|
| P1 | `electrical.dc_power_flow` (+ optional `harmonics_thd`) |
| P2 | `thermal.conduction_1d` |
| P3 | `mechanics.energy_1d` |
| P4 | `fluids.bernoulli` |
| P5 | `materials.linear_constitutive` |

## Install extras

```bash
uv sync --extra neural
uv sync --extra evolutionary
uv sync --extra neural --extra evolutionary   # hybrid X2
```
