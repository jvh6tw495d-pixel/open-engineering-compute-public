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

## Physics library consumers

Physics APIs reuse the shared registry through `oec.kernel.units`; they never
create a local Pint registry. Skills declare canonical input units with
`x-oec-unit`, and `ExecutionService` performs the single normalization pass
before the skill calls physics. Direct library callers may pass a
`QuantityValue` to `oec.physics.units.as_canonical`, which fails closed on an
incompatible dimension. Physics does not call `apply_dimensional_normalization`.

Math IR `Expr` consumers use the `oec.physics.dimensions` facade over
`modeling.dimensions.infer_dimension`; plain numeric APIs retain the reusable
physical-limit checks in `oec.validation.physical` where applicable.

| Slice | Quantity | Canonical unit |
|---|---|---|
| P1 electrical | active power; voltage; current; resistance | `W`; `V`; `A`; `ohm` (Ω) |
| P2 thermal | temperature; conductivity; heat; heat rate | `K`; `W/(m*K)`; `J`; `W` |
| P3 mechanics | length; velocity; force; energy | `m`; `m/s`; `N`; `J` |
| P4 fluids | pressure; density; velocity | `Pa`; `kg/m^3`; `m/s` |
| P5 materials | stress; density; elastic modulus | `Pa`; `kg/m^3`; `Pa` |

### Conservation tolerance policy

Every balance uses `abs(residual) <= atol + rtol * scale`. Residual, `atol`,
and scale are converted to the listed residual unit before comparison; `rtol`
is dimensionless. Incompatible units raise a structured `PhysicsUnitError`
and are never silently coerced.

| Domain | Residual unit | Default `atol` | Default `rtol` |
|---|---:|---:|---:|
| electrical | `W` | `1e-6 W` | `1e-9` |
| thermal | `W` | `1e-6 W` | `1e-9` |
| mechanics | `N` | `1e-9 N` | `1e-9` |
| fluids | `Pa` | `1e-6 Pa` | `1e-9` |
| materials | `Pa` (stress) | `1e-3 Pa` | `1e-9` |

Callers may supply an explicit compatible `atol`, `rtol`, and characteristic
scale. The returned conservation check records the effective values and unit.
