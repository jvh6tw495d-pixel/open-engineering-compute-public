# ExecutionResult contract (Phase A)

**Status:** normative for OEC 0.1.x
**Do not** replace graded status with a boolean `success` (ADR 0007).

## Top-level fields

| Field | Type | Meaning |
|---|---|---|
| `run_id` | string (UUID) | Unique id for this execution |
| `status` | `ExecutionStatus` | Graded scientific outcome (below) |
| `skill` | `{id, version}` | Skill that ran |
| `method` | `{id, version}` | Declared method (not free-form backend API) |
| `inputs` | object | Caller inputs as submitted |
| `normalized_inputs` | object | After dimensional normalization (ADR 0016) when applicable |
| `result` | object | Skill-specific payload (`output.schema.json`) |
| `assumptions` | string[] | Optional; often empty (see skill.md) |
| `conventions` | string[] | Optional; often empty (see skill.md) |
| `diagnostics` | object | Numerical / solver diagnostics |
| `validation` | object | Usually `{outcomes: [...]}` |
| `warnings` | string[] | Aggregated WARNING messages |
| `provenance` | object | Audit trail (below) |
| `started_at` / `completed_at` | datetime | UTC |
| `duration_ms` | number \| null | Wall time |

## ExecutionStatus (ADR 0007)

| Status | Intent |
|---|---|
| `VERIFIED` | Strongest: exact/closed-form or fully verified path |
| `VALIDATED` | Validated iterative success |
| `CONVERGED_WITH_WARNINGS` | Converged with warnings |
| `APPROXIMATE` | Acceptable approximate result |
| `INCONCLUSIVE` | Cannot classify cleanly |
| `INVALID` | Bad inputs / validation ERROR (not executed or rejected) |
| `FAILED` | Implementation/runtime failure or contract breach |

Interfaces may map status to HTTP/CLI exit codes differently (ADR 0014/0015); **scientific content** of the body must stay the same (ADR 0005).

## diagnostics (minimum contract)

| Skill kind | Expectation |
|---|---|
| `method.iterative: true` | Must eventually expose `converged` (bool or null for “this call exact”); missing key → FAILED (ADR 0013) |
| `method.iterative: false` | May be `{}` |

Additional keys (`n_iterations`, residuals, solver messages) are skill/backend-specific.

## provenance (Phase A1)

| Field | Meaning |
|---|---|
| `oec_version` | Package version |
| `git_commit` | Incubation repo HEAD if available |
| `trace_id` | From request |
| `requested_by` / `seed` | Optional request metadata |
| `sandbox` | What was **actually** enforced (timeout / isolation flags) |
| `units` | Original vs normalized units per field when recorded |
| `input_hash` | SHA-256 of canonical JSON of **original** `inputs` |
| `backends` | `[{name, version}, ...]` for runtime scientific engines (e.g. numpy, scipy, sympy, pint) |

`backends` lists **installed engines available to the runtime**, not a claim that every engine was invoked for that skill. Skill docs name which SciPy entry points a method uses.

## Serialization

`ExecutionResult.model_dump(mode="json")` is the public JSON shape for SDK, CLI, REST, and MCP.
