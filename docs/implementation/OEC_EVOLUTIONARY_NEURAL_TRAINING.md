# OEC — Evolutionary Neural Training (execution plan)

**Status:** accepted roadmap (implementation phased by waves)
**ADR:** [0033-evolutionary-neural-training.md](../architecture/adr/0033-evolutionary-neural-training.md)
**Date:** 2026-08-10
**Baseline:** `oec==3.4.0` + Part A (dense neural runtime) + Part B (evo depth)

## 1. Architectural decision (summary)

Three first-class modes:

```text
Gradient-Based  +  Neuroevolution  +  Hybrid Evolutionary/Gradient
```

- **Backend neural:** PyTorch
- **Backend evo:** pymoo · DEAP · Nevergrad (via OEC Evolutionary)
- **Strategic default for larger nets:** Hybrid (evolve config, train weights)

Hybrid formal loop:

\[
\phi_i=\text{config},\quad
\theta_i^*=\mathrm{Train}_{grad}(\mathcal N_{\phi_i}),\quad
F(\phi_i)=\mathrm{Eval}(\mathcal N_{\phi_i},\theta_i^*),\quad
\phi^*=\arg\max_\phi F(\phi)
\]

## 2. Gap analysis vs tree today

| Requirement | Today (3.4 + A/B) | Gap |
|-------------|-------------------|-----|
| Gradient supervised | MLP/seq/transf/GNN/AE + Part A runtime | Unified `neural.training.*` skills; RMSprop/LBFGS; SGD momentum field |
| Optimizers Adam/AdamW/SGD | Yes | Momentum, RMSprop, LBFGS |
| Hybrid HPO | `hybrid.evo_hyperparams` (Nevergrad → train_mlp) | Generalize search space, budgets, multi-obj, skill rename/alias |
| Neuroevolution (weights) | **No** | DEAP genotype + small MLP weight evo |
| Hybrid as named skill | Only hybrid.* X2 | `neural.training.hybrid` |
| Arch / feature / loss search | Partial (hidden_dims, act, lr) | Closed catalogs for residual, features mask, λ-loss |
| Multi-obj accuracy vs size | Evo multi-obj for **problems**, not neural | Wire F = (val_loss, n_params, …) |
| Strategy benchmark | Agent metrics only | `neural.benchmark.training_strategy` |
| Budgets max_eval / wall time | Part B `EvolutionaryRuntimeSpec` | Bind into hybrid + neuroevolution skills |

## 3. Modes in detail

### 3.1 Gradient-based

\[
\theta_{t+1}=\theta_t-\eta\nabla_\theta\mathcal L
\]

**Skills:** `neural.training.supervised`, `neural.training.gradient`
**Impl:** wrap Part A `TrainingRuntimeSpec` + family builders.
**Optimizers (closed):** SGD, SGD+momentum, Adam, AdamW, RMSprop, LBFGS.

### 3.2 Neuroevolution

Population \(\Theta=\{\theta^{(1)},\ldots,\theta^{(N)}\}\) evolved by
selection → mutation → crossover.

**Skill:** `neural.training.neuroevolution`
**Search may include:** weights (small nets), hparams, architecture, features,
loss weights, policies — all via **closed encodings** (vectors / integers / IR).
**Backend preference:** DEAP; pymoo for constrained multi-obj genotype search.

### 3.3 Hybrid (priority)

```text
Evo engine → φ_i → PyTorch train → validation fitness → evo → …
```

**Skill:** `neural.training.hybrid`
**Outer:** Nevergrad (black-box) or pymoo (multi-obj / constraints)
**Inner:** Part A gradient runtime with explicit `inner_training` budget.

## 4. Search spaces (closed catalogs)

### Hyperparameters
`learning_rate`, `weight_decay`, `dropout`, `batch_size`, `hidden_size` /
`hidden_dims`, `number_of_layers`, `activation`, `scheduler`, `optimizer`

### Architecture
`number_of_layers`, `width_per_layer`, `residual_connections`,
`attention_heads`, `embedding_dimension`, `activation_functions`

### Features
Binary / combinatorial subset \(S^*\subseteq\{x_1,\ldots,x_n\}\) with max
cardinality cap.

### Loss composition
\[
\mathcal L=\lambda_{a}L_{a}+\lambda_{b}L_{b}+\lambda_{c}L_{c}
\]
λ coefficients join the evolutionary search space (bounded intervals / closed catalog).

## 5. Backend matrix

| Need | Backend |
|------|---------|
| Multi-obj Pareto neural | **pymoo** (NSGA-II/III, MOEA/D) |
| Constrained config search | **pymoo** |
| Black-box HPO / portfolios | **Nevergrad** |
| Custom genotype / weight evo / GP | **DEAP** |
| Forward + backprop | **torch** |

## 6. Multi-objective neural

Simultaneous (example):

- \(\min L_{validation}\)
- \(\min N_{parameters}\)
- \(\min\) latency / memory

Output: Pareto set + HV with **fixed reference** when configured (Part B).

## 7. Reproducibility checklist

Must appear in `ExecutionResult` / provenance for evo & hybrid runs:

| Field | Source |
|-------|--------|
| seed(s) | runtime |
| population, generations, max_evaluations, max_wall_time | budget |
| mutation / crossover / selection | algorithm spec |
| backend + version | registry probe |
| fitness definition | skill + fingerprint |
| search space | problem fingerprint |
| device / hardware note | training runtime |
| dataset / model fingerprint | existing hash helpers |
| inner torch config (hybrid) | TrainingRuntimeSpec dump |

## 8. Compute budget schema (canonical)

```yaml
budget:
  max_generations: 50
  population_size: 32
  max_evaluations: 1600
  max_wall_time_s: 7200
inner_training:          # hybrid / gradient eval of a candidate
  max_epochs: 50
  early_stopping_patience: 5
  device: cpu            # or cuda / auto
```

Missing budget → **INVALID** (fail closed), not silent infinite search.

## 9. Downstream products

OEC remains **product-agnostic**. Downstream applications consume OEC skills
via SDK/MCP/REST; no proprietary product names, datasets, or branding belong
in this repository.

## 10. Target skills

```text
neural.training.supervised
neural.training.gradient
neural.training.neuroevolution
neural.training.hybrid

neural.search.hyperparameters
neural.search.architecture
neural.search.features
neural.search.loss_weights

neural.benchmark.training_strategy
```

**Migration aliases (non-breaking):**

| Existing | Maps toward |
|----------|-------------|
| `neural.mlp.regressor` / family trainers | remain; also callable from `neural.training.supervised` |
| `hybrid.evo_hyperparams` | becomes implementation core of `neural.training.hybrid` / `neural.search.hyperparameters` |
| `hybrid.surrogate_optimize` | stays physics/surrogate path (not weight training) |

## 11. Mandatory strategy benchmark

Skill `neural.benchmark.training_strategy` runs under **identical** budget:

| Arm | Path |
|-----|------|
| A | Gradient only |
| B | Evolutionary only (small net / HPO without inner train if pure evo) |
| C | Hybrid evo + gradient |

Report: val metric, generalization split, wall time, n_evaluations, n_params,
multi-seed mean±std. No arm declared superior a priori.

## 12. Implementation waves

### Wave 1 — Gradient foundation

- [x] OptimizerName: SGD momentum, RMSprop, LBFGS
- [x] `neural.training.supervised` + `neural.training.gradient`
- [x] Part A runtime provenance (`n_params`, runtime meta)

### Wave 2 — Evolutionary HPO

- [x] Expanded catalog (capacity, dropout, batch, weight_decay, optimizer)
- [x] `max_evaluations` / `max_wall_time_s` budgets
- [x] `neural.search.hyperparameters`
- [x] `hybrid.evo_hyperparams` delegates to hybrid engine

### Wave 3 — Hybrid training (strategic priority)

- [x] `neural.training.hybrid` outer/inner budgets
- [x] Fitness = val score (+ optional size via loss_weights)
- [x] Fingerprints + budget/inner_training in result
- [x] Smoke goldens

### Wave 4 — Direct neuroevolution

- [x] Nevergrad weight vector search for small MLP
- [x] `neural.training.neuroevolution` + max_params fail-closed

### Wave 5 — Multi-obj + facets + benchmark

- [x] Pareto front (rmse, n_params) among hybrid trials
- [x] `neural.search.architecture` / `features` / `loss_weights`
- [x] `neural.benchmark.training_strategy` (gradient vs hybrid vs neuro)

### Wave 6 — Feature / loss / policy evolution

- [x] `neural.search.features`
- [x] `neural.search.loss_weights`
- [x] `neural.search.policy` (short/standard/long train policies)
- [ ] RL policy evolution (future, out of core)

## 13. Success metrics (product)

| Metric | Gate idea |
|--------|-----------|
| Hybrid skill runs fail-closed without torch or nevergrad/pymoo | ERROR status |
| Budget fields always present on evo/hybrid results | unit + contract tests |
| Strategy benchmark produces three arms + multi-seed | golden under `@neural`+`@evolutionary` |
| No agent Python in fitness/arch | static + runtime allow-list |
| Part A capacity presets usable inside hybrid candidates | integration test |

## 14. Non-goals

- Free-form architecture code from agents
- Declaring hybrid always better than gradient
- Proprietary product names, datasets, or branding in the OEC tree
- Neuroevolution of LLM-scale models

## 15. Status

**W1–W6 core delivered in-tree** (kernel + 10 skills + tests). Optional polish:
DEAP structural genotype, native pymoo multi-obj for neural configs.
