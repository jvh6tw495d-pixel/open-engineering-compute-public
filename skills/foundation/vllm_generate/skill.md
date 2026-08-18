---
id: foundation.vllm_generate
version: 0.1.0
status: validated
domain: foundation
title: Remote vLLM Generation (OpenAI-compatible HTTP client)
---

# Remote vLLM generate

Calls a **running** OpenAI-compatible vLLM server (`POST /v1/completions`).
OEC does **not** install or import the `vllm` package (ADR 0046).
Requires `base_url` + `model_id` + `prompt`. No PEFT/`adapter_path`.
Unreachable server → structured `vllm_unreachable`, never invented text.
