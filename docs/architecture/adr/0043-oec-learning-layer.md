# ADR 0043: OEC Learning Layer (L1–L15)

- **Status:** accepted
- **Date:** 2026-08-16
- **Phase:** OEC Learning L1–L15
- **Related:** ADR 0021, 0034, 0035, 0038, 0040, 0041

## Context

Scientific AI 3.6 shipped skill-first neural/foundation/experiment surfaces.
The Learning architecture spec requires a **separate contract layer** so
Hugging Face, Unsloth, Axolotl, and ART remain replaceable backends — not
the public API.

## Decision

1. New package ``oec.learning`` is **core-safe** (Pydantic + stdlib only).
2. Public types: ``ModelRef``, ``LearningDataset``, ``TrainingConfig``,
   ``TrainingResult``, ``LearningExperiment``, ``MetricSpec``, ``Benchmark``,
   ``FineTuneBackend`` protocol.
3. Hugging Face lives only in ``oec.learning.backends.huggingface`` and is
   imported lazily; missing extra → structured fail-closed error.
4. Existing ``foundation.peft_train`` / generate / Experiment Engine are
   **reused**, not rewritten.
5. Waves L7–L10 implement the same protocols as fail-closed **external**
   adapters (Unsloth, Axolotl, ART/GRPO). They are integration-unverified
   and are not OEC extras. Missing packages never enter the core import
   graph.
6. L11 rewards come only from deterministic verifiers (units, constraints,
   skill status). No LLM judge.
7. L12 ``WorkerPipeline.run()`` is a demo worker, not a product.
8. L13–L14 suite + CI measure availability and contract integrity; they
   do not invent GPU metrics.

## Non-goals

- POST-OEC autonomous research harness
- Foundation-model distillation beyond the tabular ``neural.distill_mlp`` path
- Making Unsloth/Axolotl/ART structurally required

## Consequences

- Core install tests import ``oec.learning`` without torch/transformers.
- Callers choose ``backend="huggingface"``; they never import ``transformers``.
- Optional adapters fail closed with ``BackendNotAvailableError``.
