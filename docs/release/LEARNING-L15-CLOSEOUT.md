# OEC Learning L15 — programme closeout

**Branch:** `feat/learning-l1-l5`
**Baseline:** OEC 3.6.0 / tag `v3.6.0-scientific-ai`
**ADR:** 0043

## Closed

| Wave | Surface | Evidence |
|------|---------|----------|
| L1 | `oec.learning.contracts` | core-safe Pydantic + `FineTuneBackend` |
| L2 | `LearningDataset` + `store.save_dataset` | content hash + persist |
| L3 | `LearningRunRecord` + `replay_learning_experiment` | snapshot + integrity |
| L4 | `Benchmark` / `compare_results` | two runs, one protocol |
| L5 | `HuggingFaceBackend` | lazy wrap of `foundation.peft_train` |
| L6 | `distill()` | tabular → `neural.distill_mlp`; text/FM fail-closed |
| L7 | `UnslothBackend` | real FastLanguageModel path or fail-closed |
| L8 | `AxolotlBackend` + `recipe_to_experiment` | recipe ≡ Experiment |
| L9 | `rl.py` | State/Action/Trajectory/Episode |
| L10 | `ARTBackend` | `train_grpo` when `art` is present |
| L11 | `verifiers` + domain envs | no LLM judge |
| L12 | `WorkerPipeline.run()` | fail-closed without extras |
| L13 | `suite` + `measure_capability_suite` | no invented GPU metrics |
| L14 | CI `learning-contracts` | core-only, extras asserted absent |
| L15 | this note + ADR 0043 + CHANGELOG | programme closed |

## Explicitly not in this closeout

- Kronos / temporal foundation models
- POST-OEC autonomous research harness
- Foundation-model distillation (needs a future adapter)
- Live GPU A/B of Unsloth vs HF (suite is a protocol + availability probe)

## Core invariant

`import oec.learning` does not import torch, transformers, unsloth, axolotl, or art.
