# Units policy (Phase A)

**Engines:** [Pint](https://pint.readthedocs.io/) (shared registry, ADR 0011).
**Pipeline:** dimensional check then convert (ADR 0016).

## Public quantity shape

Physical inputs use a `QuantityValue`-shaped object:

```json
{ "value": 380, "unit": "V" }
```

- `value`: number
- `unit`: string parseable by the shared Pint registry

Dimensionless ratios (power factor, efficiency, pure math scalars) stay
**plain numbers**, not quantities (ADR 0003 consequence).

## Schema extension `x-oec-unit`

On a property in `input.schema.json`:

```json
"voltage_line_to_line": {
  "type": "object",
  "...": "...",
  "x-oec-unit": "V"
}
```

Means: the submitted unit must be **dimensionally compatible** with volts;
after validation, `ExecutionService` converts the field to the canonical
unit (`V`) before the skill runs.

## Pipeline order

1. Schema / skill validators (types, ranges, cross-fields)
2. `DimensionalValidator` — compatibility only (no mutation)
3. If no ERROR → `apply_dimensional_normalization`
4. Sandboxed `implementation.py` sees only canonical units

## Failure mode

Incompatible dimensions (e.g. amperes where volts are required) →
`ExecutionStatus.INVALID` with a dimensional-layer outcome. The skill
entrypoint is **not** invoked.

## Skill authors

- Do **not** re-convert units inside `implementation.py` for
  `x-oec-unit` fields.
- Document conventions (line-to-line vs phase, one-way length, etc.) in
  `skill.md`.
- Prefer SI-friendly canonical units (`V`, `A`, `W`, `m`, `ohm/m`, …).

## Merit

Unit arithmetic is Pint’s; OEC contributes the **policy** (mandatory
quantities for physical skills, central normalization, provenance hooks
for original units when recorded).
