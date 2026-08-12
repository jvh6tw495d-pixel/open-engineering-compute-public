# Skill inventory

**Updated:** 2026-08-10 (`oec==3.4.1` + W1-MVP core skills)
**Registry root:** `skills/`
**Live load:** **135** skills, **0** contract-audit errors

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
| mechanics | 1 | |
| fluids | 1 | |
| materials | 1 | |
| chemistry | 6 | |
| multiphysics | 2 | |
| **neural** | **26** | ADR 0031/0032 + **0033 training/search** |
| **evolutionary** | **15** | pymoo/DEAP/Nevergrad |
| **hybrid** | **2** | X2 surrogate + hyperparams |
| **scientific** | **1** | X3 method_select |
| **Total** | **135** | all `experimental` in this inventory |

## W1-MVP scientific core (no AI)

| Skill id | Notes |
|----------|-------|
| `statistics.distribution_eval` | SciPy pdf/cdf/ppf/mean/std/sample |
| `statistics.hypothesis_test` | t_one/t_two/ks_1samp/mannwhitney |
| `mathematics.jacobian` | multi-var FD Jacobian |
| `numerical.pde_1d_heat` | 1D FDM heat/Poisson foundation |

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
