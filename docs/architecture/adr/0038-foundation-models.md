# ADR 0038: Foundation Models (W6)

- **Status:** accepted
- **Date:** 2026-08-10
- **Phase:** Framework W6
- **Related:** ADR 0021, 0031, 0034, 0037

## Context

The scientific framework roadmap places Hugging Face Transformers **after**
neural/evolutionary compute and the Experiment Engine. Core OEC must remain
installable without multi-GB model stacks.

## Decision

1. Optional extra ``oec[foundation]`` = `transformers`, `accelerate`, `peft`.
2. Package ``oec.foundation``: closed Pydantic specs + runtime.
3. Skills:
   - ``foundation.embed`` — backends `builtin_hash` | `transformers`
   - ``foundation.generate`` — `transformers` only (fail-closed)
   - ``foundation.capabilities`` — probe without download
4. ``builtin_hash`` embeddings are **OEC-owned**, deterministic, and **not** an
   LLM merit claim (for reproducible experiments offline).
5. PEFT/LoRA/QLoRA are **schema-frozen** (`PEFTSpec`) without a full train skill
   in W6-MVP (avoids incomplete training loops).
6. Backend Registry gains ``transformers`` (+ ``sympy`` capability honesty).

## Non-goals

- vLLM / llama.cpp / SGLang runtimes (future adapters)
- Full instruction-tuning / TRL pipelines
- Auto model download as default in CI

## Consequences

- Agents must not inject arbitrary Python model code.
- Hosts check ``foundation.capabilities`` before calling generate.
