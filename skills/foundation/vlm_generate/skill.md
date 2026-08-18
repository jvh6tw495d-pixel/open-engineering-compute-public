---
id: foundation.vlm_generate
version: 0.1.1
status: validated
domain: foundation
title: Vision-Language Generation (Vision2Seq, transformers)
---

# Purpose

Generate text conditioned on a prompt and one bounded raster image with a
closed Vision2Seq architecture family via Hugging Face Transformers
(``oec[foundation]``). No generic multimodal framework, no arbitrary
model/processor code, no silent fallback to a text-only causal LM.

# Security / reproducibility (mandatory, ADR 0040 D3)

- Remote hub `model_id` values require an immutable **40-hex commit SHA**
  `revision`; branch and tag labels (including `main`) are rejected. The
  same revision is passed to every Transformers remote load. Existing local
  directory `model_id` values are the explicit local-only escape hatch.
- `trust_remote_code` is always `False` and is not exposed as an input —
  it cannot be set to `True` through this skill.
- The image is a bounded raster only: base64 bytes or a controlled local
  path with an allow-listed extension (`.png`, `.jpg`, `.jpeg`, `.webp`),
  capped at 5 MiB compressed input, 8,192 pixels per dimension, 16,000,000
  pixels, and one frame. Metadata is checked before `load()`/`convert()`;
  Pillow decompression-bomb warnings/errors become `invalid_image_source`.
  No URL fetch, ever.
- Only `AutoConfig.model_type` values in a closed VLM allow-list (BLIP /
  BLIP-2 / GIT / InstructBLIP / IDEFICS / LLaVA / PaliGemma /
  vision-encoder-decoder families) are accepted; anything else fails
  closed as `unsupported_vision_model` — this skill never falls back to
  `AutoModelForCausalLM` on a text-only base model.
- Fails closed (structured error, not an exception) when `oec[foundation]`
  or Pillow is missing, the image fails to decode, or the model/processor
  fails to load.

# Official methodology

Method id: `foundation_vlm_generate`. Merit owner: Transformers / model
card — this skill claims no generation-quality merit of its own.

# Changelog

- 0.1.1: validated — golden cases split into a fail-closed no-extra case
  (monkeypatched `probe_transformers`, structured error, no invented text)
  and a real-payload `oec[foundation]` case gated on the pinned VLM
  revision being cached locally.
- 0.1.0: S5 initial (ADR 0040 D3).
