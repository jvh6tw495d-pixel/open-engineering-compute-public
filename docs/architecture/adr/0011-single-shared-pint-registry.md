# ADR 0011: A single, shared Pint registry; no curated unit allow-list yet

- **Status:** accepted
- **Date:** 2026-07-25

## Context

ADR 0003 established the policy that physical quantities are never bare
floats and must be represented as `{"value": ..., "unit": "..."}`,
implemented via a units engine (Pint). This ADR covers the Sprint 02
implementation choices ADR 0003 deliberately left open: how the Pint
registry is instantiated, what units are allowed, how dimensional
mismatches are reported, and how normalization preserves provenance.

## Decisions

### One shared `UnitRegistry` instance

Pint quantities built from two different `pint.UnitRegistry()` instances
are not comparable or convertible, even for the exact same unit — a
well-documented Pint pitfall. `oec.kernel.units.registry.ureg` is the
single instance the whole kernel builds every `pint.Quantity` from
(`to_pint`, `from_pint`, `normalize`, `is_compatible`). No other module
may call `pint.UnitRegistry()` directly.

### No curated unit allow-list yet

Pint's default registry ships with units no engineering skill will need
(and a few joke units, e.g. `smoot`). Curating an explicit allow-list now
would be speculative — Sprint 02 has no real skill yet to derive the
list from. The registry is used as-is; curation is deferred until
Sprint 04 (math skills) and Sprint 08 (electrical skills) reveal which
units actually matter. If abuse of exotic units becomes a real problem,
that is a new ADR, not a silent change here.

### Pint's default offset-unit behavior is kept as-is

Pint raises `OffsetUnitCalculusError` on ambiguous arithmetic with
offset units (e.g. adding two temperatures in `degC`) unless
`autoconvert_offset_to_baseunit` is enabled. This is **not** enabled:
silently allowing that arithmetic could produce physically wrong results
for temperature-sensitive skills (e.g. cable/transformer derating).
Per plan instruction 10 ("não mascarar warnings de solver"), the
registry fails loudly on ambiguous unit math rather than guessing.

### `UnitError` for dimensional mismatches

`oec.errors.UnitError` extends `OECValidationError` (not `SkillError`,
since a bad unit is a validation failure that can happen outside a
skill's own manifest, e.g. an input's declared unit vs. its expected
dimensionality) and carries `from_unit`/`to_unit` in `details`. It is
raised by `normalize()` for both a real dimensional mismatch (Pint's
`DimensionalityError`) and an unrecognized target unit (Pint's
`UndefinedUnitError`) — both are "this conversion cannot happen" from a
caller's point of view, and get the same structured, catchable type.

### `normalize()` returns both the original and the converted quantity

```python
class NormalizedQuantity(BaseModel):
    original: QuantityValue
    normalized: QuantityValue
```

Rather than a bare converted `QuantityValue`, `normalize()` returns a
`NormalizedQuantity` pairing the input with the result. This is what
lets the future Skill Execution Service (Sprint 03) populate
`ExecutionResult.provenance` with the unit a caller actually submitted,
per ADR 0003's consequence ("the unit's original unit stays registered
in provenance") without Sprint 02 needing to touch the execution
pipeline itself.

### Dimensionless values stay plain numbers

`QuantityValue.unit` must be non-empty (Pint itself treats `""` as
`dimensionless`, which would silently accept a missing unit — rejected
explicitly). There is no `QuantityValue.dimensionless()` helper: a
dimensionless physical ratio (e.g. power factor) is not a `QuantityValue`
at all — it stays a plain `float` in a skill's own input schema, per ADR
0003's consequences. `QuantityValue` only models grandezas físicas.

## Consequences

- `oec.kernel.units.quantity.QuantityValue` rejects non-finite values
  (`NaN`/`Infinity`) at construction, but makes no sign assumption —
  some quantities (voltage drop, reactive power, Celsius temperature)
  can legitimately be negative. Sign constraints are a skill's own
  physical-layer validation (plan section 12.4), not a `QuantityValue`
  concern.
- `375 kW` and `0.375 MW` normalize to the same numeric value in the
  same target unit — proven by both example-based and Hypothesis
  property tests (`tests/property/test_units_properties.py`).
- A skill declaring `execution.deterministic: true` and using
  `QuantityValue` gets deterministic normalization for free: Pint's
  multiplicative unit conversions are exact floating-point operations
  with no hidden randomness.
