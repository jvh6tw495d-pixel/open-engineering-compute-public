# OEC — Neural + Evolutionary Waves (implementation status)

**Baseline:** `oec==3.3.1`
**ADR:** [0031-neural-and-evolutionary-compute.md](../architecture/adr/0031-neural-and-evolutionary-compute.md)
**Product source:** expanded from the Neural/Evolutionary roadmap (governance over engines).

## Philosophy

```text
External engine (torch / pymoo / …)
  → OEC skill contract
  → validation / governance
  → SDK / CLI / REST / MCP
```

**Not:** `LLM → arbitrary PyTorch/pymoo code`.

## Wave status

| Wave | Scope | Status |
|---|---|---|
| **N0** | Contracts, extras, capability probes | **in tree** |
| **N1** | MLP regressor / classifier / predict | **in tree (v0)** |
| **E1** | Single-objective DE / GA / CMA-ES / PSO via pymoo | **in tree (v0)** |
| **E2** | NSGA-II / NSGA-III / MOEA/D + ParetoResult | **in tree (v0)** |
| **X1 thin** | `evolutionary.benchmark` multi-algo × multi-seed | **in tree (v0)** |
| **N2** | Autoencoder basic + denoising | **in tree (v0)** |
| **N3** | CNN1D / LSTM / GRU / TCN sequences | **in tree (v0)** |
| **N4** | Transformer encoder (not LLM) | **in tree (v0)** |
| **N5** | GCN / GraphSAGE / GAT pure torch (ADR 0032) | **in tree (v0)** |
| **E3** | Genetic programming + ES (DEAP, operator IR) | **in tree (v0)** |
| **E4** | Black-box + optimizer portfolio (Nevergrad) | **in tree (v0)** |
| **X2** | Hybrid surrogate+evo + evo hyperparams | **in tree (v0)** |
| **X3** | `scientific.method_select` agent routing | **in tree (v0)** |

## Install

```bash
uv sync --extra neural
uv sync --extra evolutionary   # pymoo + deap + nevergrad
# or both
uv sync --extra neural --extra evolutionary
```

## Skills (v0)

### Neural

- `neural.mlp.regressor` / `classifier` / `predict` / `evaluate` (N1)
- `neural.autoencoder.basic` / `denoising` (N2)
- `neural.cnn1d` / `lstm` / `gru` / `tcn` (N3)
- `neural.transformer.encoder` / `sequence_regressor` / `sequence_classifier` (N4)
- `neural.gcn` / `graphsage` / `gat` (N5, pure torch — ADR 0032)

### Evolutionary

- `evolutionary.optimize_single` — dispatch by algorithm name
- `evolutionary.differential_evolution`
- `evolutionary.genetic_algorithm`
- `evolutionary.cma_es`
- `evolutionary.pso`
- `evolutionary.nsga2` / `nsga3` / `moead` — multi-objective (E2)
- `evolutionary.pareto_search` — multi-obj dispatch
- `evolutionary.benchmark` — X1 thin harness (single or multi)
- `evolutionary.genetic_programming` / `evolution_strategy` / `custom_ga` (E3 DEAP)
- `evolutionary.blackbox_optimize` / `optimizer_portfolio` (E4 Nevergrad)

### Hybrid / Scientific (X2–X3)

- `hybrid.surrogate_optimize` — sample → MLP surrogate → evo → **true-f verify**
- `hybrid.evo_hyperparams` — Nevergrad over closed MLP hyperparam catalog
- `scientific.method_select` — capability-aware skill recommendation (+ optional probe)

## Safety

- Closed architecture / algorithm enums only
- Optional backends: missing extra → verification ERROR
- Stochastic skills require `seed`
- Neural/evo results are **not** physics conservation claims

## Follow-on design (dense neural + evo depth + evolutionary neural training)

See **[OEC_DENSE_NEURAL_AND_EVO_MATURITY.md](./OEC_DENSE_NEURAL_AND_EVO_MATURITY.md)** for:

- **Part A done:** shared neural runtime + capacity presets for all families;
- **Part B done:** expression IR objectives, inequality constraints, multi-seed matrix,
  fixed HV reference (`EvolutionaryRuntimeSpec` / `run_seed_matrix`).

See **[OEC_EVOLUTIONARY_NEURAL_TRAINING.md](./OEC_EVOLUTIONARY_NEURAL_TRAINING.md)** and
**[ADR 0033](../architecture/adr/0033-evolutionary-neural-training.md)** for the
**three-mode** neural training roadmap:

```text
Gradient-Based  +  Neuroevolution  +  Hybrid (evo config → PyTorch train)
```

Waves W1–W6 **implemented** (gradient → HPO → hybrid → neuroevolution →
multi-obj/Pareto search facets → feature/loss/policy evolution + strategy benchmark).

## Existing hybrid seed (maps to W2/W3)

- `hybrid.evo_hyperparams` — Nevergrad outer, `train_mlp` inner (closed catalog)
- `hybrid.surrogate_optimize` — sample → MLP surrogate → evo → true-f verify (not weight training)
