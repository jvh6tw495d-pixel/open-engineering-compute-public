---
id: foundation.generate
version: 0.2.0
status: experimental
domain: foundation
title: Causal LM Text Generation (transformers)
---

# Purpose

Generate text with a causal LM via Hugging Face Transformers
(``oec[foundation]``). Fail-closed when the extra is missing.

Optionally reloads a trained adapter/checkpoint produced by
`foundation.peft_train` via `adapter_path` (S1, ADR 0041 §3). A missing or
unloadable adapter path fails closed — generation never silently falls
back to the bare base model without provenance.

# Official methodology

Method id: `transformers_generate`. Merit owner: Transformers / model card.

# Changelog

- 0.2.0: S1 — optional `adapter_path` reload (ADR 0041).
- 0.1.0: W6 initial.
