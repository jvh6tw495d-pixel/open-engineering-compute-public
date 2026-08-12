# ADR 0041: PEFT, Fine-Tune & Distillation Contracts (S1–S2)

- **Status:** accepted
- **Date:** 2026-08-12
- **Phase:** Scientific AI S1–S2
- **Related:** ADR 0021, 0031, 0033, 0034, 0035, 0038, 0040

## Context

ADR 0038 froze `PEFTSpec` without a train skill (W6-MVP). Scientific AI
Completion requires governed PEFT / fine-tune paths and knowledge distillation
under the Experiment Engine, still fail-closed and free of arbitrary agent code.

`oec[foundation]` already declares `peft` as a dependency; the Backend Registry
already lists capability domain `foundation_peft` for `transformers`.

## Decision

### 1. PEFT (S1 primary)

1. Extend / version `PEFTSpec` (schema ≥ `0.2.0` when training fields land) with:
   - closed `PEFTMethod`: `lora` | `qlora` | `none`
   - rank / alpha / dropout / target_modules (closed string set + allow-list)
   - **training budget hard caps**: `max_steps`, `max_seq_len`, `batch_size` upper bounds
   - dataset as **inline texts** or **local path label** (no silent hub dataset download in core path)
2. Public skill **`foundation.peft_train`**:
   - requires `oec[foundation]`
   - runtime uses PEFT + Transformers only behind `oec.foundation` adapters
   - returns adapter artifact ref (`path` or inline blob policy) + `sha256` + provenance
3. QLoRA requires bitsandbytes **only if** present; otherwise fail-closed with structured error
   (do not invent quantized weights).

### 2. Full fine-tune (S1 secondary)

1. Skill **`foundation.finetune`** **or** a `method: full` mode on the same skill
   family — implementers prefer **one skill with closed training mode enum**
   (`peft_lora` | `peft_qlora` | `full`) to avoid catalog sprawl.
2. Full FT restricted to **tiny models** and hard step caps suitable for smoke CI
   (`sshleifer/tiny-gpt2` class).

### 3. Artifacts & reload

1. Training skills MUST emit a machine-readable artifact descriptor:
   - `kind`: `adapter` | `checkpoint`
   - `path` (when file storage) and/or content hash
   - `base_model_id` + `revision`
2. `foundation.generate` (and future eval) MAY accept optional adapter/checkpoint
   ref; missing extra or missing file → fail-closed, never silent base-model swap
   without provenance.

### 4. Knowledge distillation (S2)

1. Primary skill domain for 3.6: **`neural.distill`** (tabular teacher→student).
   - `DistillationSpec`: teacher checkpoint/ref, student closed architecture knobs,
     temperature, loss mix weights (closed enum), budget caps.
2. Foundation LM distillation is **non-goal for S2** unless S1 artifacts make a
   minimal path trivial; if added later, skill id `foundation.distill`.
3. Experiment builder: `build_distill_then_eval_experiment` on the W7-style
   allow-list catalog only.

### 5. Backend registry

| Backend | Domains (additive) |
|---------|-------------------|
| `transformers` | `foundation_embed`, `foundation_generate`, `foundation_peft`, `foundation_finetune` |
| `torch` | existing neural + `neural_distill` when S2 lands |

No new required core backends.

## Skill IDs (planned)

| Skill | Wave | Extra |
|-------|------|--------|
| `foundation.peft_train` | S1 | foundation |
| `foundation.finetune` (or mode on peft_train) | S1 | foundation |
| `neural.distill` | S2 | neural |

## Non-goals

- TRL full SFT/DPO/RLHF product pipelines
- Multi-GPU distributed training
- Arbitrary PEFT target module strings from agents without allow-list
- Hub dataset auto-download as default

## Consequences

- ADR 0038 item “PEFT schema freeze without train skill” is **superseded for S1**:
  train skill becomes mandatory for Scientific AI DoD.
- Existing `PEFTSpec` remains source of truth until schema_version bump in code.
- Implementation must keep core tests green without peft/transformers installed.
