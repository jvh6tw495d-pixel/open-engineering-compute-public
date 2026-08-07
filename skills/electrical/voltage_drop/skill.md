---
id: electrical.voltage_drop
version: 0.1.0
status: experimental
domain: electrical
title: Voltage Drop
---

# Purpose

Compute the absolute and percent voltage drop along a single-phase or
balanced three-phase feeder, given either a known current or a known
active power, conductor resistance (directly or via material +
cross-section), optional reactance, and an explicit one-way length
convention.

# Problem definition

Given system voltage `V_ref`, load current (or power + power factor),
one-way conductor route length `L`, resistance per unit length `R`
(and optional reactance per unit length `X`), compute the voltage drop
`ΔV` and `ΔV / V_ref * 100`.

# Supported problem classes

- **Single-phase, current known**: `ΔV = 2 · I · L · (R cosφ ± X sinφ)`.
- **Three-phase balanced, current known** (line-to-line):
  `ΔV = √3 · I · L · (R cosφ ± X sinφ)`.
- **Current derived from active power** for either phase count
  (`load_type: power`), using the same current formulas as
  `electrical.current_from_power`.
- **Resistance from material + cross-section** (IEC 60228 resistivities
  at 20 °C) as an alternative to supplying `resistance_per_length`.

# Required inputs

- `load_type` (`current` | `power`).
- `phase_count` (`1` | `3`).
- `voltage_reference` (`QuantityValue`, `x-oec-unit: "V"`): nominal
  system voltage (single-phase line voltage, or three-phase
  line-to-line). Denominator of `voltage_drop_percent`; also `V` when
  deriving current from power.
- `power_factor` (number, `0 ≤ PF ≤ 1`).
- `length` (`QuantityValue`, `x-oec-unit: "m"`): **one-way** conductor
  route length. The single-phase formula applies the out-and-back
  factor of 2 internally — do **not** double this value yourself.

Conditionally required:

- `current` iff `load_type: current` (rejected for `power`).
- `power` (active) iff `load_type: power` (rejected for `current`).
- Either `resistance_per_length` **or** both `material` and
  `cross_section` (not both paths).

# Optional inputs

- `power_factor_type` (`lagging` | `leading`, default `lagging`):
  selects `+ X sinφ` (lagging) or `− X sinφ` (leading).
- `reactance_per_length` (`QuantityValue`, `x-oec-unit: "ohm/m"`,
  default `0`): common omission for small conductors where reactance
  is negligible relative to resistance.

# Units and dimensions

All `QuantityValue` fields are converted to their canonical units by
`ExecutionService` before this skill runs (ADR 0016). `power_factor` is
dimensionless.

# Official methodology

Closed-form approximate voltage-drop formula used in low-voltage
feeder sizing (ABNT NBR 5410 style). No solver, no method selection
(`method.iterative: false`).

# Mathematical formulation

Let `cosφ = power_factor`, `sinφ = sin(acos(PF))`, and

```
Z_term = R·cosφ + X·sinφ    (lagging)
Z_term = R·cosφ − X·sinφ    (leading)
```

```
Single-phase:  ΔV = 2 · I · L · Z_term
Three-phase:   ΔV = √3 · I · L · Z_term   (line-to-line)
percent      = 100 · ΔV / V_ref
```

When `load_type: power`:

```
Single-phase:  I = P / (V_ref · PF)
Three-phase:   I = P / (√3 · V_ref · PF)
```

When resistance is derived from material:

```
R = ρ / A
```

with `ρ_copper = 0.017241 Ω·mm²/m`, `ρ_aluminum = 0.028264 Ω·mm²/m`
(IEC 60228 at 20 °C) and `A` in mm² → `R` in Ω/m.

# Assumptions

- Balanced three-phase only.
- Uniform conductor along `L`; ambient/temperature correction of
  resistivity is out of scope (values fixed at 20 °C).
- Approximate phasor projection formula (not a full load-flow).
- `length` is one-way route length, not round-trip.

# Conventions

- Three-phase `voltage_reference` and `ΔV` are line-to-line.
- `length` is one-way; single-phase multiplies by 2 internally.
- Negative `ΔV` (voltage rise) is reported as-is for strongly leading
  loads with non-zero `X` — not absolute-valued.

# Applicability limits

- Not a cable ampacity or short-circuit study.
- No temperature coefficient, skin effect, or non-linear loads.
- Unbalanced feeders out of scope.

# Validation rules

`VoltageDropValidator` (`layer: physical`):

- Cross-field rules for `load_type` ↔ `current`/`power`.
- Exactly one resistance path: `resistance_per_length` XOR
  (`material` + `cross_section`).
- Positivity of voltage, length, current/power, resistance,
  cross-section; `reactance_per_length ≥ 0`.

# Numerical diagnostics

`diagnostics` is always `{}` — exact closed-form, no convergence
concept.

# Alternative methods

Full series impedance phasor calculation or multi-node load-flow would
be separate future skills.

# Failure conditions

- Missing/extra load or resistance fields → `INVALID`.
- Non-positive physical magnitudes → `INVALID`.
- Dimensionally incompatible units → `INVALID`.
- No `FAILED`/`INCONCLUSIVE` path for a valid input.

# Worked examples

See `examples/`. Single-phase: 10 A, 230 V, PF 0.8 lagging, 50 m,
R = 0.001 Ω/m, X = 0 → `ΔV = 0.8 V` (0.348%).

# References

See `references.md`.

# Known limitations

- Fixed 20 °C resistivities; no temperature correction.
- Approximate formula only.
- No neutral/ground conductor modeling.

# Changelog

- 0.1.0: initial version (Sprint 08).
