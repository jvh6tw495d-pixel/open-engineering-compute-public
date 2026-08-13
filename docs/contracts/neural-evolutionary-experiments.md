# Neural & Evolutionary experiments (W4/W5)

**ADRs:** 0031, 0033, 0034, 0037

## Neural (W4)

```python
from oec.sdk import Engine
from oec.neural.contracts import DatasetSpec
from oec.experiment import build_mlp_regressor_experiment

engine = Engine(skills_root="skills")
ds = DatasetSpec(
    x=[[0.0], [1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0]],
    y=[1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0],
    val_fraction=0.25,
)
spec = build_mlp_regressor_experiment(
    dataset=ds,
    seed=0,
    epochs=40,
    hidden_dims=[16],
    lr=0.05,
    lr_scheduler="cosine",  # none | cosine | step
)
record = engine.run_experiment(spec)
# metric: result.train_metrics.r_squared
```

Training modes (ADR 0033):

```python
from oec.experiment import build_neural_training_mode_experiment
spec = build_neural_training_mode_experiment(mode="hybrid", dataset=ds, seed=0)
```

Requires `oec[neural]` (and `oec[evolutionary]` for hybrid/neuroevolution).

## Evolutionary (W5)

```python
from oec.experiment import build_optimize_single_experiment, sphere_problem_2d
from oec.evolutionary.contracts import EvolutionaryAlgorithmSpec, BudgetSpec, AlgorithmName

spec = build_optimize_single_experiment(
    problem=sphere_problem_2d(),
    algorithm=EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
        budget=BudgetSpec(generations=20, population=16),
        seed=0,
    ),
    max_objective=0.1,
)
record = engine.run_experiment(spec)
# metric: result.best_objective
```

NSGA-II:

```python
from oec.experiment import build_nsga2_experiment
spec = build_nsga2_experiment(n_var=5, generations=15, population=20, seed=0)
```

## Hybrid (W4 ∩ W5)

```python
from oec.experiment import build_hybrid_training_experiment
spec = build_hybrid_training_experiment(x=..., y=..., seed=0, max_evaluations=6)
```

## Catalog surface (S4)

Public declarative builders discoverable via MCP/CLI
(`experiment.list_builders` / fail-closed `experiment.run` builder names):

- `build_optimize_single_experiment` — extras: `evolutionary`
- `build_nsga2_experiment` — extras: `evolutionary`
- `build_hybrid_training_experiment` — extras: `neural`, `evolutionary`
- plus W7 compositions such as `build_evo_sphere_experiment`

Helpers (`sphere_problem_2d`, `problem_to_optimize_inputs`) and non-catalog
factories (`build_mlp_regressor_experiment`, `build_evo_then_describe_experiment`)
are **not** MCP builder names.

## Excluded / out of scope

- **NEAT / HyperNEAT** — **excluded from 3.6 DoD** (ADR 0042; deferred since ADR 0037).
  Existing neuroevolution remains `neural.training.neuroevolution` + hybrid (ADR 0033),
  not topology-evolution genotype engines.
- Foundation models / HF — W6 / Scientific AI S1+
