# ADR 0024: Physics library architecture (`src/oec/physics/`, layering, domain objects, envelope schema 1.1, conservation ownership)

- **Status:** Draft — Wave 0; accept on Wave 6
- **Date:** 2026-08-03
- **Phase:** v2.6.0 "Physics Foundation P1–P5 v0", Wave 0–1 (`docs/implementation/
  v2.6-EXECUTION-PLAN.md`, decisions D2, D3, D5)

## Context

`OEC_V3_IMPLEMENTATION_PLAN.md` §10 defines a "Physics Complete" roadmap
milestone spanning domain objects (`PhysicalLaw`, `ConservationLaw`,
`MaterialProperty`, `BoundaryCondition`) and slices P1–P5 (electrical,
thermal, mechanics, fluids, materials). Before this ADR, physical law lives
nowhere as a first-class package: electrical skills (`skills/electrical/*`,
ADR 0016) embed their own formulas directly in `implementation.py`, and
`oec.kernel.energy.metrics.energy_balance` is the only generic conservation
check, scoped to energy alone. `oec.modeling` is Math IR — domain-agnostic
expression/dimension machinery (ADR 0020) — and is not the right home for
domain physics; folding P1–P5 into it would break its no-domain-knowledge
contract.

An independent audit (`docs/implementation/v26-CODEX-DEPENDENT-AUDIT.md`
§B) raised three risks against the original v2.6 draft plan that this ADR
closes: (1) the closed v1.0 `kind` enum in
`schemas/authoritative_answer.schema.json` (L16–28) has no `physics_result`
value, and adding one "while keeping schema 1.0" is a silent contract
break, not an additive extension; (2) `PhysicalLaw`/`ConservationLaw` could
ship as decorative types that only serialize, never execute; (3) a second,
independently-drifting conservation formula could appear alongside
`kernel.energy.metrics.energy_balance` with no declared owner.

## Decision

### 1. New package `src/oec/physics/`, layered above kernel/modeling

`src/oec/physics/` is a new top-level package, sibling to `oec.modeling`
and `oec.kernel`, not a subpackage of either:

```
skills/{electrical,thermal,mechanics,fluids,materials}.*
        ↓
oec.physics          ← NEW: laws, conservation, per-domain models, domain objects
        ↓
oec.modeling.dimensions   oec.kernel.units   oec.kernel.energy (unchanged)   oec.core
```

`oec.physics` may import `oec.modeling`, `oec.kernel.*`, `oec.validation`, and `oec.core`.
`oec.modeling` never imports `oec.physics` — the IR stays domain-agnostic.
`oec.physics` must not import `oec.mcp`, `oec.api`, `oec.agents`, or
`skills.*` (no upward or lateral imports into interface/execution layers);
a Wave 1 layering test enforces this by import-graph inspection, and any
cycle is an automatic NO-GO at GATE-W1. `oec.physics` imports zero private
decision-engine code (ADR 0008) — it exposes only public, generalizable
physical laws.

### 2. Domain objects are executable, not decorative

`PhysicalLaw`, `ConservationLaw`, `MaterialProperty`, and `BoundaryCondition`
(`src/oec/physics/laws.py`) are frozen, immutable types (Pydantic frozen or
equivalent, aligned with `oec.core`) carrying id/name, structured
hypotheses (reusing `oec.core.Assumption` where it fits, rather than
forking a second hypothesis system), a validity domain, and references.
Declaring these types is necessary but not sufficient: Wave 1 requires each
of `PhysicalLaw` and `ConservationLaw` to expose a callable execution path
(instantiate **and** evaluate a residual / apply the law), demonstrated by
a smoke test invoking it against at least two stub domains. Wave 3 raises
the bar to acceptance: at least two of the P1–P5 slices must call through
`PhysicalLaw`/`ConservationLaw` to produce a real result, not merely
construct and dump the object as JSON. `MaterialProperty` carries units and
is consumed by P5 (and by any other slice that needs it).
`BoundaryCondition` is an auditable metadata declaration (type, value,
unit, target entity) attached to the models that accept it in v0; a model
that does not yet consume a `BoundaryCondition` must say so explicitly
rather than leaving the field referenced nowhere.

Result shapes (`PhysicsResult`, `ConservationCheck` in
`src/oec/physics/result.py`) are stable dicts or Pydantic frozen models
with `extra="forbid"`, carrying `residual`, `balanced`, `atol`, `rtol`,
`scale`, and the residual's unit — never a single collapsing `success: bool`
(see ADR 0025 for the tolerance policy itself). This result type is
internal to `oec.physics` and is distinct from the MCP
`authoritative_answer` envelope (ADR 0023); the two are related only
through the mapping in §3 below.

### 3. Envelope evolves to schema 1.1 with kind `physics_result` — Wave 4 only

The v1.0 `kind` enum (`schemas/authoritative_answer.schema.json`) is closed
and does not include `physics_result`. Rather than smuggling the new kind
into "schema 1.0" — which would validate envelopes the published schema
was never designed to accept — the schema versions forward to **1.1**:
1.0 plus `physics_result` appended to the enum, with a corresponding bump
to the schema's own `"version"` field. Schema 1.0 remains valid for every
envelope already emitting v1.0 kinds; nothing existing is invalidated.
`authoritative_answer_schema_version` (ADR 0023 §1) continues to carry the
per-envelope version string; it stays `"1.0"` for `electrical.*` paths
(kind `energy_result`, unchanged — the existing classic electrical skills
are not migrated) and becomes `"1.1"` the first time a skill under a new
domain prefix (`thermal.*`, `mechanics.*`, `fluids.*`, `materials.*`) is
normalized and mapped to `physics_result` in `_KIND_BY_PREFIX`
(`src/oec/mcp/envelope.py`).

This is deliberately scoped to a **single** wave: Wave 1–3 must not touch
`envelope.py` or `schemas/authoritative_answer.schema.json` "to get ahead"
of this decision — `physics_result` appearing in code without the
matching schema 1.1 bump, in the same wave, is a stop condition (v2.6
plan §12 item 15). Wave 4 lands the schema bump, the `_KIND_BY_PREFIX`
entries, and `jsonschema` Draft 2020-12 validation tests against real
envelopes in the same commit. `docs/contracts/authoritative-answer.md` is
updated in the same wave. ADR 0023's wrap-once mechanism and the
`claimed_answer`/divergence channel are unchanged by this bump — this is
an additive enum/version change, not a redesign of the envelope.

### 4. Conservation ownership: `oec.physics.conservation` is the source of truth

`src/oec/physics/conservation.py` is the single owner of generic
conservation-check logic (energy, charge, mass/continuity, and residual
computation across domains). `oec.kernel.energy.metrics.energy_balance`
remains the kernel's existing, stable, energy-scoped API and becomes a
**consumer/adapter** of that ownership, not a second independent formula:
in 2.6.0 the two are parity-documented (same Σin − Σout − Δstorage residual
semantics, verified by parity tests) without rewriting
`kernel.energy.metrics` itself (zero churn — its `tolerance: float`
parameter is not touched this release). A future release may thin-wrap
`energy_balance` to call `oec.physics.conservation` directly, provided
golden numbers are unchanged; that is explicitly out of scope for 2.6.0.
Two independently-computed, potentially-diverging formulas for the same
residual are never acceptable — any PR introducing a second one is an
automatic re-gate trigger (v2.6 plan §12 item 14).

## Non-goals (this release)

- Rewriting or migrating the six classic `electrical.*` skills — P1 adds
  `dc_power_flow` alongside them (ADR 0026); their golden tests are
  unchanged.
- Multiphysics coupling between P1–P5 slices (V3 §11) — deferred to v2.7,
  which needs a coupling-readiness contract this release does not define.
- Energy-rich modules (storage/PV/hybrid/grid-zero/service_metrics) —
  deferred to v2.6.1 (see the sibling `v2.6.1-EXECUTION-PLAN.md`), which
  inherits this ADR's conservation ownership and does not reopen it.
- Rewriting `kernel.energy.metrics.energy_balance` itself to the
  `atol + rtol×scale` tolerance form (ADR 0025) — tracked as residual debt,
  not required this release.
- Any change to `ExecutionResult`'s shape or to the count/identity of MCP
  tools exposed — `oec.physics` is a library, not a skill engine.

## Consequences

- Skills across all five domains share one place for physical law and one
  place for conservation checking, instead of each skill re-deriving
  balance/residual logic independently.
- The envelope's `kind` taxonomy grows in a versioned, backward-compatible
  way (1.0 → 1.1) rather than an invisible enum mutation that would make
  schema-validating hosts either reject valid physics envelopes or silently
  accept envelopes the published 1.0 schema never promised to accept.
- `PhysicalLaw`/`ConservationLaw` carry real executable weight from Wave 1
  onward, so the risk flagged in the Codex audit — domain objects that
  exist only to be instantiated and JSON-dumped — is closed by construction
  (test-gated) rather than by intent alone.
- Any future consumer of `energy_balance` and `oec.physics.conservation`
  can trust they agree on the same residual semantics, because there is
  exactly one owner of the formula and the other is a documented,
  parity-tested adapter.
- Residual, not closed by this ADR: whether `kernel.energy.metrics` is
  ever rewritten to call `oec.physics.conservation` directly, and whether
  v2.7 multiphysics coupling changes how `ConservationCheck` composes
  across domains, are both open questions for later releases.

## References

- `docs/implementation/v2.6-EXECUTION-PLAN.md` §0 (D2, D3, D5), Wave 1,
  Wave 3, Wave 4, §12, §16 (DoD), §18 (ADR table)
- `docs/implementation/v26-CODEX-DEPENDENT-AUDIT.md` §B risks 1, 4, 6
- ADR 0023 (authoritative-answer envelope, wrap-once, `kind` taxonomy)
- ADR 0020 (Math IR foundation — `oec.modeling` domain-agnostic boundary)
- ADR 0016 (central dimensional normalization)
- ADR 0008 (public/private separation, forbidden names)
- `schemas/authoritative_answer.schema.json` (enum L16–28, version L6)
- `src/oec/kernel/energy/metrics.py` (`energy_balance`)
