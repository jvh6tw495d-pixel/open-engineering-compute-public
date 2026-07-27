# ADR 0019: oec.core.ScientificResult — additive adapter over ExecutionResult

- **Status:** accepted
- **Date:** 2026-07-26
- **Phase:** A1 (core consolidation)

## Context

`oec.execution.models.ExecutionResult` is the Skill Engine's auditable outcome
and already carries the full provenance/inputs/diagnostics payload (ADR 0007,
ADR 0017). Domain skills, REST/MCP clients, and benchmark agents all consume it
directly. However, `ExecutionResult` is an **execution** record: it couples the
scientific outcome to engine-specific fields (`skill`, `method`, `inputs`,
`normalized_inputs`, `conventions`) that downstream scientific consumers should
not have to depend on.

Task K7 asked for a stable, domain-independent scientific outcome type in
`oec.core` that can be handed to reviewers, notebooks, and external pipelines
without re-importing the Skill Engine contract.

## Decision

Add **`oec.core.ScientificResult`** as an **additive adapter** built from
`ExecutionResult`. Concretely, in `src/oec/core/scientific_result.py`:

1. **Do not break `ExecutionResult`.** It remains the canonical Skill Engine
   output; REST `/v1/skills/{id}/run`, MCP, and the SDK keep returning it
   unchanged. No field is removed or renamed on `ExecutionResult`.
2. **`oec.core` stays independent of domain skill packages.** `ScientificResult`
   imports only `oec.core.types` (`Assumption`, `BackendRef`, `MethodRef`) and
   `oec.execution.models` (for the adapter); it must not import any skill module.
3. **`from_execution_result(er: ExecutionResult) -> ScientificResult`** performs
   a **non-mutating** field mapping with no boolean `success` collapse:

   | `ExecutionResult`        | `ScientificResult` |
   |---------------------------|--------------------|
   | `run_id`                  | `run_id`           |
   | `status: ExecutionStatus` | `status`           |
   | `skill` (`VersionedRef`)  | `skill_id` + `skill_version` |
   | `method` (`VersionedRef`) | `method: MethodRef` |
   | `result`                  | `value`            |
   | `assumptions: list[str]`  | `assumptions: list[Assumption]` (`source="execution"`) |
   | `diagnostics`             | `diagnostics: list[Diagnostic]` + `diagnostics_raw` |
   | `warnings`                | `warnings`         |
   | `validation`              | `validation`      |
   | `provenance`              | `provenance: ProvenanceRecord` |
   | `provenance["backends"]`  | `backends` property → `ProvenanceRecord.backends` |
   | `started_at` / `completed_at` / `duration_ms` | same |
   | *(optional caller)*       | `validity: ValidityDomain | None` |

   `inputs`, `normalized_inputs`, and `conventions` are intentionally **not**
   forwarded: they belong to the execution layer, not the scientific outcome.

`ScientificResult` re-exports from `oec.core` (`from oec.core import
ScientificResult, from_execution_result`) so the public core surface name is
stable; `ExecutionStatus` is imported by value (no `success` boolean is added).

## Consequences

- Existing consumers of `ExecutionResult` keep working unmodified — the adapter
  is purely additive and the REST/MCP/SDK response models are untouched.
- `oec.core` gains a read-only scientific outcome type without depending on any
  skill package, preserving the core-vs-domain layering in ADR 0001.
- Reviewer/agent code can now narrate from `ScientificResult` instead of the
  execution record, while the Skill Engine remains the single source of truth
  for `run_id`, `status`, and `provenance`.
- Future core-level transformations (normalized-units view, reduced narrative
  projection, etc.) can be added as additional adapters returning
  `ScientificResult` without further widening `ExecutionResult`.
