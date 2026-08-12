# ADR 0035: Scientific Spec Family v0

- **Status:** accepted
- **Date:** 2026-08-10
- **Phase:** Framework W0 freeze
- **Related:** ADR 0017 (provenance), ADR 0031 (neural contracts), **0034** (experiment)

## Context

The framework roadmap requires a shared vocabulary of **specs** so that Core,
Applied Sciences, Neural, Evolutionary, and Foundation Models compose under one
experiment model. Today only neural training has first-class Pydantic specs
(`DatasetSpec`, `NeuralModelSpec`, `TrainingSpec` in `oec.neural.contracts`).
Provenance exists as a **record** (`ProvenanceRecord`), not as an input policy
spec. Metrics and artifacts are free-form inside skill results.

## Decision

### 1. Spec family (v0 field freeze)

All specs are Pydantic models with:

- `schema_version: Literal["0.1.0"]` (or field default)
- `model_config = ConfigDict(frozen=True, extra="forbid")`
- JSON round-trip stable for tests

| Spec | Role | Notes |
|------|------|-------|
| `ExperimentSpec` | Full experiment plan | Owns steps, seed, env requirements |
| `DatasetSpec` | Data declaration | **General** envelope; neural tabular arrays are a *kind* |
| `ModelSpec` | Model declaration | Discriminated union by `kind` (neural, …) |
| `TrainingSpec` | Train/search budget | May embed or reference neural training knobs |
| `MetricSpec` | Named metric + direction | Resolved from ExecutionResult paths |
| `ValidationSpec` | Gates / thresholds | Complements skill `ValidationPolicy` |
| `ArtifactSpec` | Expected or produced artifact | Checkpoints, tables, figures |
| `ProvenanceSpec` | What to record | Policy; `ProvenanceRecord` remains the runtime fact |

### 2. Location

```text
src/oec/experiment/
  __init__.py
  specs.py      # family v0 (this ADR)
  # runner.py   # W2
  # record.py   # W2
```

Neural-specific names remain importable from `oec.neural` for compatibility.
W0 does **not** break `oec.neural.contracts.DatasetSpec`; coexistence is
allowed until a dedicated migration wave renames the neural type to
`TabularArrayDataset` (or equivalent) and re-exports aliases.

### 3. ExperimentStep (minimal)

```text
step_id: str
skill_id: str
skill_version: str | None
inputs: dict          # concrete JSON inputs for v0
# binds_from / templates: reserved for W2 runner enhancements
```

v0 allows **concrete inputs only** (no template language required for stubs).
W2 may add `inputs_template` + `binds_from` without changing `schema_version`
if additive; otherwise bump to `0.2.0`.

### 4. Non-goals

- Implementing the runner in W0
- Full Dataset lake / remote URIs
- HuggingFace model cards as ModelSpec
- Boolean `success` on experiments (use `ExperimentStatus` enum in W2)

## Consequences

- Unit tests lock JSON schema shape for each spec
- W1 skills may optionally *reference* MetricSpec ids in docs; not required
- W2 runner is the first consumer of `ExperimentSpec.steps`

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Only skill.yaml as experiment | No multi-step composition |
| Free-form dict without pydantic | No freeze, no agent-safe validation |
| Force-migrate neural DatasetSpec in W0 | Unnecessary churn before runner exists |
