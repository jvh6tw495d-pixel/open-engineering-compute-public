# ADR 0033: Evolutionary Neural Training Modes

- **Status:** accepted (roadmap decision)
- **Date:** 2026-08-10
- **Phase:** OEC 3.5+ (post Part A dense neural + Part B evo depth)
- **Supersedes / extends:** ADR 0031 (neural + evolutionary compute), ADR 0032 (GNN)

## Context

OEC 3.4 ships optional **PyTorch** neural skills and **pymoo/DEAP/Nevergrad**
evolutionary skills under governance-over-engines. Part A added a shared
dense neural runtime; Part B added expression IR and multi-seed evo depth.
`hybrid.evo_hyperparams` already implements a thin **hybrid** slice
(Nevergrad outer → MLP train inner).

Product requirement: the neural roadmap must **explicitly** support three
training / optimization modes:

1. **Gradient-based** (PyTorch backprop)
2. **Neuroevolution** (direct evolutionary search over weights / structure)
3. **Hybrid evolutionary + gradient** (preferred for larger nets)

Agents must not inject arbitrary `nn.Module` or fitness Python. All search
spaces remain closed catalogs / IR.

## Decision

### Three modes (mandatory product model)

| Mode | Merit engines | Skill family (target ids) |
|------|---------------|---------------------------|
| **Gradient-based** | torch | `neural.training.supervised`, `neural.training.gradient` |
| **Neuroevolution** | deap (+ optional pymoo) | `neural.training.neuroevolution` |
| **Hybrid evo→gradient** | nevergrad/pymoo outer + torch inner | `neural.training.hybrid` |

Formal hybrid loop (strategic default for non-toy nets):

```text
Evolutionary Engine
        ↓
  candidate config φ_i  (arch / hparams / loss weights / …)
        ↓
  θ*_i = Train_gradient(N_φi)   # PyTorch backprop
        ↓
  F(φ_i) = Evaluate(N_φi, θ*_i)
        ↓
  next generation → φ*
```

\[
\phi_i=\text{candidate config},\quad
\theta_i^*=\mathrm{Train}_{gradient}(\mathcal N_{\phi_i}),\quad
F(\phi_i)=\mathrm{Evaluate}(\mathcal N_{\phi_i},\theta_i^*),\quad
\phi^*=\arg\max_\phi F(\phi)
\]

**Do not** evolve millions of weights when backprop is available; evolve
**configuration**, train **weights** with gradients.

### Backend roles (evolutionary)

| Backend | Prefer for |
|---------|------------|
| **pymoo** | multi-objective (NSGA-II/III, MOEA/D), DE, constraints, Pareto |
| **DEAP** | experimental neuroevolution, custom EA, GP, custom genotypes |
| **Nevergrad** | black-box HPO, gradient-free, optimizer portfolios |

PyTorch remains the sole neural merit owner for forward/backward.

### Optimizer catalog (gradient mode)

Closed enum (extend `OptimizerName` over waves):

| Wave | Optimizers |
|------|------------|
| W1 (now → expand) | Adam, AdamW, SGD (momentum as field) |
| W1.x | RMSprop, LBFGS |

### Search spaces (closed)

All search dimensions are **declarative catalogs**, not free Python:

- **Hyperparameters:** `learning_rate`, `weight_decay`, `dropout`, `batch_size`,
  `hidden_size` / `hidden_dims`, `number_of_layers`, `activation`, `scheduler`,
  `optimizer`
- **Architecture:** layers, width, residual, attention heads, embedding dim,
  activations (enum)
- **Features:** subset \(S^*\subseteq\{x_1,\ldots,x_n\}\) via index masks /
  allow-lists
- **Loss composition:** e.g. \(\mathcal L=\lambda_{a}L_{a}+\lambda_{b}L_{b}+\lambda_{c}L_{c}\)
  with λ coefficients in the closed search space

### Multi-objective neural training

Supported objectives (simultaneous via pymoo multi-obj skills):

- minimize validation loss / regret
- minimize \(N_{params}\)
- minimize latency / memory / compute

Produce a **Pareto front**; no single “best” without stated trade-off policy.

### Reproducibility (mandatory fields)

Every evolutionary or hybrid run records at least:

- `seed`, `population_size`, `generations`, `evaluation_budget`
- mutation / crossover / selection (when applicable)
- backend + version (torch, pymoo|deap|nevergrad)
- fitness definition + search space fingerprint
- hardware / device, dataset fingerprint, model fingerprint
- hybrid only: full inner PyTorch training config (epochs, optimizer, early stop, …)

### Compute budget (fail closed without)

No evolutionary search runs without explicit termination:

```yaml
budget:
  max_generations: 50
  population_size: 32
  max_evaluations: 1600
  max_wall_time_s: 7200
inner_training:          # hybrid only
  max_epochs: 50
  early_stopping_patience: 5
```

Aligns with Part B `EvolutionaryRuntimeSpec` (`max_evaluations`, `max_seconds`, seeds).

### Proposed skills (target catalog)

**Training modes**

- `neural.training.supervised` — thin alias / unified supervised entry
- `neural.training.gradient` — explicit gradient path + optimizer catalog
- `neural.training.neuroevolution` — direct evo of weights/structure (DEAP-first)
- `neural.training.hybrid` — evo outer + gradient inner (**priority**)

**Search facets**

- `neural.search.hyperparameters`
- `neural.search.architecture`
- `neural.search.features`
- `neural.search.loss_weights`

**Benchmark**

- `neural.benchmark.training_strategy` — controlled comparison under shared budget

Existing skills remain: family trainers (`neural.mlp.*`, sequences, …),
`hybrid.evo_hyperparams` (seed of hybrid), `hybrid.surrogate_optimize`.

### Benchmark obligation

Under **shared budgets**, compare:

| Strategy | Engine path |
|----------|-------------|
| Gradient only | torch |
| Evolutionary only | deap/pymoo/nevergrad neuroevolution or black-box |
| Hybrid evo + gradient | outer evo + inner torch |

Metrics: validation performance, generalization, compute/GPU time, evaluations,
model size, multi-seed stability. **No strategy is superior by definition.**

### Waves

| Wave | Scope | Depends on |
|------|--------|------------|
| **W1** | Supervised gradient training + MLP + Adam/AdamW/SGD(+momentum) + reproducibility | Part A runtime (done) |
| **W2** | Evolutionary HPO (pymoo and/or Nevergrad) over closed catalogs | Part B runtime (done), expand `hybrid.evo_hyperparams` |
| **W3** | **Hybrid** evo + gradient training skill (`neural.training.hybrid`) — strategic priority | W1 + W2 |
| **W4** | Direct neuroevolution (DEAP) for small nets / experimental | W2 |
| **W5** | Multi-objective neural (accuracy vs size vs latency) + architecture/feature/loss search facets + strategy benchmark | W3 |
| **W6** | Feature evolution, loss-weight evolution, **policy evolution** (closed training-policy catalog) | W5 |

### Formal rule

Neural training is **not** backprop-only:

\[
\text{Neural Training} = \text{Gradient} \cup \text{Evolutionary} \cup \text{Hybrid}
\]

PyTorch remains the neural engine; OEC Evolutionary supplies search; OEC governs
contracts, budgets, validation, and provenance.

**Official integration:** \(\text{OEC Neural} \leftrightarrow \text{OEC Evolutionary}\).

## Consequences

- Extend optimizer enum and training contracts without breaking ADR 0031.
- Hybrid is the **default recommendation** for capacity beyond toy MLPs.
- Direct neuroevolution stays **experimental** and budget-capped (small models).
- New skills stay `experimental` until benchmark gates + multi-seed reports pass.
- CI: gradient path in `@neural`; hybrid/neuroevolution require both extras.

## Non-goals

- Free Python fitness / architecture injection
- Claiming global optimality of any search
- Evolving full large-model weight tensors as first-class path
- Downstream product-specific datasets or branding inside the OEC core wheel

## Related

- ADR 0031 neural/evolutionary compute
- ADR 0032 pure-torch GNN
- `docs/implementation/OEC_DENSE_NEURAL_AND_EVO_MATURITY.md` (Part A/B)
- `docs/implementation/OEC_EVOLUTIONARY_NEURAL_TRAINING.md` (execution plan)
- Skills: `hybrid.evo_hyperparams`, `hybrid.surrogate_optimize`
