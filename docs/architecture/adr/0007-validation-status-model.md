# ADR 0007: The seven `ExecutionStatus` values, precisely

- **Status:** accepted
- **Date:** 2026-07-25

## Context

`ExecutionStatus` (`oec.execution.models`, defined in Sprint 00) has
seven values — `VERIFIED`, `VALIDATED`, `CONVERGED_WITH_WARNINGS`,
`APPROXIMATE`, `INCONCLUSIVE`, `INVALID`, `FAILED` — deliberately instead
of a boolean `success`. Sprint 00 defined the enum; it did not define
*when* each value applies. Sprint 03's Validation Engine and Execution
Service are the first code that actually assigns a status, so that
mapping has to be nailed down before either is implemented — otherwise
two validator layers written independently (this sprint splits work
between Claude Code and Grok, see `docs/sprints/sprint-03-*.md`) would
invent incompatible meanings.

## Decision

Status is assigned by the Execution Service after all applicable
validation layers have run, using this precedence (first match wins,
checked top to bottom):

| Status | Condition |
|---|---|
| `FAILED` | The skill's implementation raised an unhandled exception, exceeded `timeout_seconds`, or otherwise did not produce a result at all. No `result` is available. |
| `INVALID` | A pre-execution validator (schema, dimensional, mathematical domain, or physical limits) reported an **error**-severity outcome, so the implementation never ran; **or** a post-execution invariant check reported an error-severity outcome on an otherwise-produced result. |
| `INCONCLUSIVE` | The implementation ran and returned a result, but numerical diagnostics show the method did not converge (or otherwise failed to reach a usable solution) and the result cannot be trusted even as an approximation. |
| `APPROXIMATE` | The implementation ran and returned a result from a method that is inherently approximate by design (e.g. truncated series, linearization) **or** converged only to a coarser-than-requested tolerance — usable, but explicitly weaker than a converged result. |
| `CONVERGED_WITH_WARNINGS` | The method is exact or converged to tolerance, **and** at least one validator layer reported a **warning**-severity outcome (e.g. a physical value near an applicability boundary, poor numerical conditioning). |
| `VALIDATED` | The method is iterative/numerical, its diagnostics report `converged: true` (or equivalent), and every validation layer passed with zero warnings. |
| `VERIFIED` | The method is exact/closed-form — no iterative convergence is even applicable (e.g. Ohm's law, a direct algebraic formula) — and every validation layer passed with zero warnings. This is the strongest claim: no numerical approximation was involved at all. |

`VERIFIED` is **not** "compared against a golden case at runtime" —
golden case comparison (plan section 12.6) is a *testing* concern
(`tests/golden/`, run by pytest against stored expected values), not
something the Execution Service can do for arbitrary production inputs
it has never seen before. Conflating the two would make `VERIFIED`
nearly unreachable in real use and would misrepresent what golden tests
actually check (development-time regression protection, not per-call
runtime proof).

`VALIDATED` vs `VERIFIED` is the exact/iterative distinction, not a
"more" vs "less" checked distinction — both require every validation
layer to pass cleanly with zero warnings. A method's `MethodRef`
(`SkillManifest.method`) doesn't currently declare "exact" vs
"iterative"; until it does, a skill implementation reports this
explicitly via `diagnostics["converged"]`: `None`/absent means exact
(no convergence concept applies → eligible for `VERIFIED`), `true`/
`false` means iterative (eligible for `VALIDATED`/`INCONCLUSIVE`
respectively, given no warnings).

## Consequences

- A skill never has to guess which status to return — the Execution
  Service computes it mechanically from validator outcomes and the
  `converged` diagnostic, per skills only report raw diagnostics, not a
  status.
- `INVALID` and `FAILED` are cleanly separable in logs/telemetry: a
  malformed request (`INVALID`) is a caller problem; a crash or timeout
  (`FAILED`) is an implementation or environment problem.
- A solver reporting `converged: true` is necessary but not sufficient
  for `VALIDATED` — plan section 3's requirement that "solver convergido
  não implica automaticamente resultado validado" (section 33, Sprint 03
  gate) is satisfied structurally: convergence only reaches `VALIDATED`
  after every other validator layer has also passed.
- This table is the contract both Claude Code's `ExecutionService` and
  Grok's validator layers are written against — a validator layer only
  needs to return `(layer, severity, messages)` outcomes; it never
  computes `ExecutionStatus` itself.
