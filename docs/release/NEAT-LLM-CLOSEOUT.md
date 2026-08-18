# NEAT + HF LLM reference path — closeout

**Date:** 2026-08-17
**Scope:** promote five existing skills from `experimental` to `validated`.
This is **not** a new engine — NEAT (ADR 0044) and the Hugging Face
foundation surface (W6/S1, ADR 0038/0040/0041) already existed. "Close"
means an honest validated lifecycle, goldens that do not accept
`"error" OR "success"` as a pass, and a written record of what is — and is
not — covered.

## Promoted (`experimental` → `validated`, patch version bump)

| Skill id | Version | Method id |
|---|---|---|
| `evolutionary.neat` | 0.1.0 → 0.1.1 | `neat_python_feedforward` (unchanged) |
| `foundation.generate` | 0.2.0 → 0.2.1 | `transformers_generate` (unchanged) |
| `foundation.peft_train` | 0.1.0 → 0.1.1 | `transformers_peft_train` (unchanged) |
| `foundation.embed` | 0.1.0 → 0.1.1 | `foundation_embed` (unchanged) |
| `foundation.capabilities` | 0.1.0 → 0.1.1 | `foundation_capabilities_probe` (unchanged) |

`skill.yaml` and `skill.md` front matter carry the same `status`/`version`
for all five (the loader cross-checks the two and rejects disagreement).
Method ids are unchanged — this is a lifecycle promotion, not a rewrite.

**Not promoted** (stay `experimental`): `foundation.vision_embed`,
`foundation.vlm_generate`, every other evolutionary skill (pymoo/DEAP/
Nevergrad/GP/blackbox), and HyperNEAT (never implemented — see below).

## NEAT (`evolutionary.neat`)

- Entry point: `skills/evolutionary/neat` → `oec.kernel.evolutionary.neat.run_neat()`.
- Experiment builder: `oec.experiment.evolutionary.build_neat_experiment`,
  catalogued on the fail-closed cross-domain builder registry
  (`experiment.list_builders` reports `domains: ["evolutionary"]`,
  `extras: ["evolutionary"]`).
- **Closed fitness catalog** (`NeatFitnessName`, ADR 0044): `xor`,
  `tabular_regression`, `tabular_classification`. No caller-supplied Python
  fitness function — this is intentional; running arbitrary caller code
  inside the evolutionary loop is out of scope.
- Requires the `oec[evolutionary]` extra (`neat-python`). Missing extra
  raises `NeatNotAvailableError` (`neat_not_available`), asserted directly
  by `tests/unit/test_neat_governed.py::test_fail_closed_when_neat_missing`
  via `monkeypatch.setitem(sys.modules, "neat", None)` — no network or
  extra-uninstall needed to exercise the fail-closed path.
- The golden case (`skills/evolutionary/neat/tests/test_golden.py`,
  `pytest.importorskip("neat")`, `-m evolutionary`) requires a **real**
  genotype IR (node/connection counts, `best_fitness` as a float) when
  `neat-python` is installed. It does not require XOR to be solved —
  `best_fitness` is asserted to exist and be finite, not to hit a target.
- The result carries an OEC-owned genotype IR (nodes + connections), never
  a raw `neat-python` genome object.
- **HyperNEAT is not implemented and is not promoted or claimed anywhere
  in this closeout.**

## HF LLM reference path (`foundation.*`)

Four skills under `skills/foundation/`, all requiring the `oec[foundation]`
extra (`transformers`; `peft_train` additionally needs `peft`, and QLoRA
additionally needs `bitsandbytes` + CUDA). The core install stays free of
transformers/PEFT.

### `foundation.generate`

- Causal LM text generation via `oec.foundation.runtime.generate_text`.
- **Honesty fix (this closeout):** `filesystem_access` was `false` in the
  manifest even though `adapter_path` reloads a trained adapter directory
  from disk (S1, ADR 0041 §3). Now `true`, matching actual behavior.
- Adapter reload requires `adapter_sha256` — `_require_adapter_sha256`
  refuses to load an adapter directory without a pinned digest and refuses
  a digest mismatch. There is no silent fallback to the bare base model.
- Golden: `skills/foundation/generate/tests/test_golden.py` now splits into
  `test_missing_extra_fails_closed` (monkeypatches
  `oec.foundation.runtime.probe_transformers` to simulate the missing
  extra — always runs, asserts a structured `{code, message, details}`
  error, no `text` key) and `test_real_payload_with_extra`
  (`pytest.importorskip("transformers")`, `-m foundation`, asserts a real
  generated `text` string against the locally cached `sshleifer/tiny-gpt2`
  fixture model).

### `foundation.peft_train`

- LoRA / QLoRA / full fine-tune via `oec.foundation.runtime.peft_train`.
  Training data is always caller-supplied (inline `texts` or a local
  `dataset_path` label) — never a silent Hugging Face Hub dataset download.
- **QLoRA is a real NF4 4-bit path**, not a LoRA alias: it builds a real
  `BitsAndBytesConfig` (`load_in_4bit=True`, `nf4`, double-quant) and
  requires both `bitsandbytes` and `torch.cuda.is_available()`. CPU-only
  QLoRA fails closed with `BitsAndBytesNotAvailableError`
  (`bitsandbytes_not_available`) rather than silently downgrading to
  full-precision LoRA — use `mode=peft_lora` on CPU.
  `bitsandbytes` is not installed in this dev environment, so the QLoRA
  success path is not exercised by the test run recorded below; the
  fail-closed contract (missing package **or** missing CUDA) is what's
  covered.
- Saves the trained adapter/checkpoint to disk and returns a
  machine-readable artifact descriptor (`kind`, `path`, `sha256`,
  `base_model_id`, `revision`) so `foundation.generate` can reload it with
  provenance via `adapter_path` + `adapter_sha256`.
- Golden: split into `test_missing_extra_fails_closed` (structured error,
  no `artifact` key), `test_real_artifact_with_extra` (`-m foundation`,
  real LoRA adapter written under a temp `artifact_root`, `kind == "adapter"`,
  a real sha256, `steps_run == max_steps`), and `test_full_mode_real_checkpoint`
  (`mode=full` maps to `PEFTMethod.NONE`, `kind == "checkpoint"`). The
  pre-existing `test_mutually_exclusive_dataset_fields_reported` (texts +
  dataset_path both set → pydantic validation error, independent of the
  extra) is unchanged.

### `foundation.embed`

- Closed backend catalog: `builtin_hash` (OEC-owned deterministic vector,
  explicitly not an LLM — used as the default so embeddings work with no
  extra installed) and `transformers` (mean-pooled `AutoModel` hidden
  states, requires the extra).
- Golden: `test_example_builtin_embed` (deterministic, always real) plus
  two new cases for the `transformers` backend —
  `test_transformers_backend_missing_extra_fails_closed` (structured error,
  no `vectors` key) and `test_transformers_backend_real_payload_with_extra`
  (`-m foundation`, real vectors of the requested `dim` against the cached
  fixture model). Previously the `transformers` backend had no golden
  coverage at all.

### `foundation.capabilities`

- Pure probe (`oec.foundation.runtime.foundation_capabilities`) — reports
  `transformers_available` / `peft_available` / `pillow_available` and
  their versions without downloading any model. It never raises, so there
  is no fail-closed/real-payload split to make; the existing golden already
  asserts the real report shape unconditionally.

## Fail-closed contract summary

| Missing dependency | Error | Code |
|---|---|---|
| `neat-python` (`oec[evolutionary]`) | `NeatNotAvailableError` | `neat_not_available` |
| `transformers` (`oec[foundation]`) | `TransformersNotAvailableError` | `transformers_not_available` |
| `peft` (adapter reload/train) | `PeftNotAvailableError` | `peft_not_available` |
| `bitsandbytes` or CUDA (QLoRA) | `BitsAndBytesNotAvailableError` | `bitsandbytes_not_available` |
| adapter dir missing / unpinned / digest mismatch | `AdapterNotFoundError` / `FoundationError` | `adapter_not_found` / `foundation_error` |

## Explicitly out of scope (not implemented, not promoted, not claimed)

- **vLLM / llama.cpp / SGLang** — no alternate inference backend exists;
  `foundation.generate` is a plain Transformers `generate()` call.
- **HyperNEAT** — not implemented under `evolutionary.neat` or anywhere
  else.
- **Foundation-model text/task distillation** — `oec.learning` L6
  `distill()` covers tabular distillation via `neural.distill_mlp` only;
  text/FM distillation still fails closed (see
  `docs(learning): drop Kronos from the Learning programme`).
- **Kronos** — dropped from the Learning programme prior to this closeout.
- **VLM promotion** — `foundation.vision_embed` and `foundation.vlm_generate`
  stay `experimental`. They are correct and fail-closed (closed model-type
  allow-lists, pinned revisions, Pillow decompression-bomb guards) but were
  not in scope for this closeout and were not re-reviewed here.

## Tests run

```
uv run pytest tests/unit/test_neat_governed.py tests/unit/test_s4_evo_builder_catalog.py -q --no-cov
uv run pytest tests/unit/test_neat_runtime.py skills/evolutionary/neat/tests/test_golden.py -q --no-cov -m evolutionary
uv run pytest skills/foundation/generate/tests skills/foundation/peft_train/tests skills/foundation/embed/tests skills/foundation/capabilities/tests -q --no-cov
uv run pytest skills/foundation/generate/tests skills/foundation/peft_train/tests skills/foundation/embed/tests skills/foundation/capabilities/tests -q --no-cov -m foundation
```

All pass in this environment (`neat-python`, `transformers`, `peft`
installed; `bitsandbytes` not installed — QLoRA success path untested here,
its fail-closed path is). See the CHANGELOG `Unreleased` entry and
`docs/implementation/skill-inventory.md` for the catalog-level record.
