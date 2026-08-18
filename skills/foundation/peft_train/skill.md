---
id: foundation.peft_train
version: 0.1.1
status: validated
domain: foundation
title: PEFT / Full Fine-Tune Training (transformers + peft)
---

# Purpose

Train a LoRA/QLoRA adapter, or run a full fine-tune, on a causal LM via
Hugging Face Transformers + PEFT (``oec[foundation]``). Fail-closed when
the extra (or, for QLoRA, ``bitsandbytes``) is missing. Saves the trained
adapter/checkpoint to disk and returns a machine-readable artifact
descriptor (`kind`, `path`, `sha256`, `base_model_id`, `revision`) that
`foundation.generate` can reload via `adapter_path`.

Training data is always supplied by the caller — inline `texts` or a
`dataset_path` local file label — never a silent Hugging Face Hub dataset
download.

# Modes

- `peft_lora` / `peft_qlora`: wrap the base model with a LoRA adapter
  (`r`, `lora_alpha`, `lora_dropout`, `target_modules` — the last is a
  closed allow-list, not arbitrary attribute paths). QLoRA additionally
  requires `bitsandbytes`.
- `full`: trains all base-model parameters. Restricted in practice to
  tiny models by the hard `max_steps`/`max_seq_len`/`batch_size` caps —
  suitable for smoke CI (`sshleifer/tiny-gpt2` class), not production FT.

# Official methodology

Method id: `transformers_peft_train`. Merit owner: PEFT / Transformers.

# Changelog

- 0.1.1: validated — golden cases split into a fail-closed no-extra case and
  a real-artifact `oec[foundation]` case; QLoRA fails closed without
  `bitsandbytes`/CUDA.
- 0.1.0: S1 initial (ADR 0040/0041).
