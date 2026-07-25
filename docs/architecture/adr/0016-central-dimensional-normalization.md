# ADR 0016: Dimensional normalization is a central `ExecutionService` step, not a per-skill responsibility

- **Status:** accepted
- **Date:** 2026-07-25

## Context

Sprint 08 (Fase A) is the first sprint whose skills — the six
electrical skills the master handbook §14.2 names
(`three_phase_power`, `current_from_power`, `voltage_drop`,
`power_factor_correction`, `transformer_loading`,
`per_unit_conversion`) — actually need `QuantityValue`-shaped inputs
(voltage, current, power, impedance) for real, rather than the
dimensionless math every `mathematics.*` skill so far has used.

The mechanism to represent and convert those quantities already
existed from Sprint 02 (ADR 0003, ADR 0011): `QuantityValue`, a shared
Pint registry, `normalize()`, and the `x-oec-unit` JSON Schema
extension `DimensionalValidator` already reads to *check* compatibility
(`oec.validation.dimensions`). What never got wired up — flagged as
explicitly deferred in `ExecutionService`'s own module docstring since
Sprint 03 — was the second half: actually **converting** a compatible
but non-canonical unit (`0.38 kV`) to the canonical one (`380 V`)
before a skill's `implementation.py` runs.

Two places that conversion could live:

1. **Per skill**: each electrical skill's `implementation.py` calls
   `oec.kernel.units.normalize.normalize()` itself, in whatever shape
   it wants.
2. **Central, in `ExecutionService`**: one pipeline step converts every
   `x-oec-unit`-declared field before any skill entrypoint ever runs.

This was put to the project owner directly (per handbook §18: methodology
approval for engineering skills is the owner's call, unlike the
pure-math skills built so far) rather than decided unilaterally, since
getting it wrong is expensive to unwind across six skills built on top
of it.

## Decision

**Normalization is centralized in `ExecutionService`.** Every input a
skill's `input.schema.json` declares an `x-oec-unit` for is converted
to that canonical unit before the sandboxed `implementation.py` ever
receives it — a skill's entrypoint never does its own unit conversion
and never has to guard against receiving the "wrong" (but dimensionally
compatible) unit for a field it declared.

### Pipeline shape

```
resolve skill
  -> run input validators (schema / dimensional / mathematical / physical)
  -> if no ERROR outcome:
       -> apply_dimensional_normalization (NEW)
       -> execute in sandbox
  -> run result validators
  -> ...
```

`apply_dimensional_normalization` (`oec.execution.normalization`) only
runs after every input validator — critically,
`DimensionalValidator` — has already reported no `ERROR`. For a skill
with `validation.dimensional: true` (the `ValidationPolicy` default),
that means every `x-oec-unit`-declared field is already confirmed
convertible. Conversion therefore **cannot itself fail**: it is a pure
value substitution, not a second validation pass. This is deliberate —
the `InputValidator`/`ResultValidator` protocols were frozen in Sprint
03 (`docs/architecture/adr/0012-subprocess-execution-sandbox.md`'s
sibling contract-freeze work) specifically so validators stay
side-effect-free (`validate() -> list[ValidationOutcome]`, no mutation
of the inputs they're checking). Rather than reopening that frozen
contract to let a validator also return converted values, normalization
is a distinct, later pipeline step — the same way sandbox execution
itself is already gated on "no input validator reported an ERROR."

A field's compatibility is therefore checked in exactly one place
(`DimensionalValidator`) and converted in exactly one other
(`apply_dimensional_normalization`) — never both reporting the same
mismatch, never both silently disagreeing about whether a value is
convertible.

### Shared helpers, not duplicated schema-reading

`DimensionalValidator` and `apply_dimensional_normalization` both need
to answer "which fields does this schema declare a canonical unit for"
and "does this value look like a `QuantityValue`". That logic now
lives once, in `oec.kernel.units.schema` (`declared_units`,
`is_quantity_dict`) — the kernel layer, so both the validation layer
and the execution layer can import it without a new
validation↔execution circular dependency.

### `ExecutionResult.normalized_inputs` gets real semantics

This field already existed (populated as a passthrough copy of
`request.inputs` since Sprint 03). It now reflects genuine
post-conversion values whenever execution actually ran — `.inputs`
still preserves exactly what the caller submitted (per ADR 0003: the
original unit is never lost), `.normalized_inputs` is what the skill's
`implementation.py` actually received.

## Consequences

- Every future electrical skill's `implementation.py` can read
  `inputs["voltage"]["value"]` directly, trusting it's already in the
  unit its own schema declared — no skill re-implements unit
  conversion, and six skills can't drift into six slightly different
  conventions for it.
- `validation.dimensional: false` (no electrical skill should ever set
  this, but a future skill author could) also disables normalization —
  a skill that opts out of dimensional *validation* gets no conversion
  either; declaring `x-oec-unit` while also setting
  `dimensional: false` is a skill-authoring contradiction this ADR
  does not specially detect or reject.
- No manifest schema change was needed — `x-oec-unit` already existed
  as the declaration point; this ADR only wires the conversion that was
  always the other half of that declaration's purpose.
- This does not touch `QuantityValue`, `normalize()`, or the shared
  Pint registry (ADR 0011) — only where in the pipeline `normalize()`
  gets called from.
