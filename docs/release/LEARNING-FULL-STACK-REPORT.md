# Full-stack Learning experiment

**Date:** 2026-08-16
**Builder:** `build_full_stack_learning_experiment`
**Record:** `COMPLETED`
**config_hash:** `dea8f1c22620dad0157e04be0ea05f090650a865d573b754c4983c6fa68e72a7`
**dataset_hash:** `d3aa8e5cf81517c92b1d2154a4c7589f6bc68c4df29b612423c0dc4960865841`

One `ExperimentSpec`, nine skills, smoke budgets. Metrics are measured, not quality claims.

## Pipeline

```
AG (sphere) → NSGA-II → MLP teacher → distill → evaluate
         → hybrid (evo+grad) → embed → PEFT LoRA → generate (adapter reload)
```

| Step | Skill | Status | Measured |
|---|---|---|---|
| ag | `evolutionary.optimize_single` (`genetic_algorithm`) | VALIDATED | best f = **0.00246** at x≈(−0.027, −0.041); 80 evals |
| nsga2 | `evolutionary.nsga2` | VALIDATED | **8** non-dominated; 40 evals |
| train | `neural.mlp.regressor` | VALIDATED | 20 epochs, train R² **−0.23**, MAE 7.02 |
| distill | `neural.distill` (teacher bound from train) | VALIDATED | 8 epochs, student train R² **−2.76** |
| evaluate | `neural.evaluate` (student checkpoint bound) | VERIFIED | R² **−3.05**, MAE 12.12, n=12 |
| hybrid | `neural.training.hybrid` | VALIDATED | mode=`hybrid` |
| embed | `foundation.embed` (`builtin_hash`) | VERIFIED | dim=8, n=2 |
| peft | `foundation.peft_train` LoRA tiny-gpt2 | VALIDATED | 1 step; sha256 `0cdf8549…` |
| generate | `foundation.generate` + bound `adapter_path` | VALIDATED | text `OEC stairs stairs…` (tiny model, 1 step) |

Validation gates: **passed**.

## How to repeat

```bash
cd C:\tmp\oec-3.6-integration
uv run python -c "from oec.experiment import build_full_stack_learning_experiment; from oec.sdk import Engine; r=Engine(skills_root='skills').run_experiment(build_full_stack_learning_experiment()); print(r.status)"
```

Or `oec experiment` with the catalog name `build_full_stack_learning_experiment`.

Learning dataset persist: `C:\tmp\oec-full-stack-out\learning-dataset`. JSON: `C:\tmp\oec-full-stack-out\record.json`.

ART / Unsloth / Axolotl were **not** called. They still fail closed unless `oec learning bootstrap` is used.
