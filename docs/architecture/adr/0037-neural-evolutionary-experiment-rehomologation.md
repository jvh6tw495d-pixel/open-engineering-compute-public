# ADR 0037: Neural & Evolutionary re-homologation under Experiment (W4/W5)

- **Status:** accepted
- **Date:** 2026-08-10
- **Phase:** Framework W4 + W5 after Experiment Engine (W2) and Applied Sciences (W3)
- **Related:** ADR 0031, 0033, 0034, 0035

## Context

OEC 3.4.x already ships rich **neural** (26) and **evolutionary** (15) skills
with Pydantic contracts (`oec.neural`, `oec.evolutionary`). The Experiment
Engine (W2) provides the universal scientific run contract. W4/W5 must **not**
rewrite those skills; they must expose them as first-class experiments.

## Decision

1. **Sugar builders** (importable without torch/pymoo):
   - `oec.experiment.neural` — `build_mlp_regressor_experiment`, training-mode builders
   - `oec.experiment.evolutionary` — `build_optimize_single_experiment`, `build_nsga2_experiment`,
     `build_hybrid_training_experiment`, `PopulationSpec` (= `BudgetSpec`)
2. **Re-homologation** means:
   - contracts → skill inputs → `ExperimentSpec` → `ExperimentRecord`
   - metrics resolved only from `ExecutionResult` paths
   - `required_extras` declares `neural` / `evolutionary`
3. **Hybrid W4↔W5** uses existing `neural.training.hybrid` (ADR 0033) as an
   experiment step; no new hybrid kernel.
4. **NEAT / HyperNEAT** are **explicitly deferred** (not in W5-MVP). Future work
   under a dedicated ADR; no half-implemented skill stubs.
5. **No arbitrary agent Python** remains in force (no free `nn.Module`, no
   fitness `eval`).

## Consequences

- Callers prefer:

  ```python
  from oec.experiment import build_mlp_regressor_experiment, run_experiment

  record = engine.run_experiment(build_mlp_regressor_experiment(dataset=...))
  ```

- Skills remain the unit of execution; builders are pure planning.
- Industrial promotion of skill `status` remains W8.

## Non-goals

- Hugging Face / foundation models (W6)
- Full NEAT genotype engines
- Replacing skill I/O schemas
