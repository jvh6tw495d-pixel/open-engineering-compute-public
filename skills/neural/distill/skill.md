---
id: neural.distill
version: 0.1.0
status: experimental
domain: neural
title: Governed Tabular Neural Distillation
---

# Governed Tabular Neural Distillation

Trains a bounded regression MLP student from a supplied local teacher checkpoint and labeled tabular arrays.

Requires `oec[neural]`. The teacher checkpoint must originate from an OEC-compatible MLP training result. No hub downloads, arbitrary model code, or free-form architectures are accepted.

The S2 implementation supports scalar regression only. `temperature` is therefore fixed to `1.0`; it is retained as an explicit contract field for a future logits-based classification extension.
