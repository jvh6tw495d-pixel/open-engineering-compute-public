# OEC Learning L15 — status (not a product close)

**Branch:** `feat/learning-l1-l5`
**Baseline:** OEC 3.6.0 / tag `v3.6.0-scientific-ai`
**ADR:** 0043

Status vocabulary: `contract-complete` | `core-tested` | `integration-unverified` | `demo-only` | `deferred`.

| Wave | Surface | Status |
|------|---------|--------|
| L1 | `oec.learning.contracts` | `core-tested` |
| L2 | `LearningDataset` + persist | `core-tested` (hash includes provenance) |
| L3 | `LearningRunRecord` + `ReplayReport` | `core-tested` (rerun, not bit-identical replay) |
| L4 | `Benchmark` / `compare_results` | `core-tested` |
| L5 | `HuggingFaceBackend` | `core-tested` isolation; live train is extra-dependent |
| L6 | `distill()` + teacher checkpoint | `core-tested` tabular path |
| L7 | `UnslothBackend` | `integration-unverified` (external package) |
| L8 | `AxolotlBackend` + `recipe_to_experiment` | `integration-unverified` |
| L9 | `rl.py` | `contract-complete` |
| L10 | `ARTBackend` | `integration-unverified` |
| L11 | `verifiers` + domain envs | `core-tested` |
| L12 | `WorkerPipeline` | `demo-only` |
| L13 | `suite` + `measure_capability_suite` | `core-tested` |
| L14 | CI `learning-contracts` | `core-tested` |
| L15 | this note | honest status matrix |

## Explicitly deferred

- Kronos / temporal foundation models
- POST-OEC autonomous research harness
- Foundation-model distillation
- Live GPU A/B of Unsloth vs HF
- OEC extras for Unsloth/Axolotl/ART (would enter `uv sync --all-extras`)

## Core invariant

`import oec.learning` does not import torch, transformers, unsloth, axolotl, or art.
