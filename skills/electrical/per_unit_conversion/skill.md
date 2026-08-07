---
id: electrical.per_unit_conversion
version: 0.1.0
status: experimental
domain: electrical
title: Per-Unit Conversion
---

# Purpose

Convert electrical quantities between actual units and the classical
per-unit system, and change the base of a per-unit impedance.

# Problem definition

Given voltage and power bases (and phase count), either:

- convert an actual `Z/V/I/S` to per-unit,
- convert a per-unit value back to actual units, or
- retarget a per-unit impedance from one `(V_base, S_base)` pair to
  another.

# Supported problem classes

- `to_per_unit` for impedance, voltage, current, or power.
- `from_per_unit` for the same four kinds.
- `change_base` for impedance-style base change
  `Z_pu,new = Z_pu,old · (S_new/S_old) · (V_old/V_new)²`.

# Required inputs

- `operation` (`to_per_unit` | `from_per_unit` | `change_base`).
- `phase_count` (`1` | `3`).
- `voltage_base` (`QuantityValue`, `x-oec-unit: "V"`).
- `power_base` (`QuantityValue`, `x-oec-unit: "W"`).

Conditionally required — see validation rules.

# Optional inputs

None beyond operation-specific fields.

# Units and dimensions

Bases are normalized by ADR 0016. Free-form `value` for
`to_per_unit` is checked for dimensional compatibility with the
chosen `quantity_kind` inside this skill's validator (it cannot carry
a single static `x-oec-unit` because the unit depends on
`quantity_kind`).

# Official methodology

Classical power-system per-unit definitions (Glover / Grainger).

# Mathematical formulation

```
Single-phase:  I_base = S_base / V_base
               Z_base = V_base / I_base = V_base² / S_base
Three-phase:   I_base = S_base / (√3 · V_LL,base)
               Z_base = V_LL,base / (√3 · I_base) = V_LL,base² / S_base
```

```
Z_pu = Z / Z_base
V_pu = V / V_base
I_pu = I / I_base
S_pu = S / S_base
Z_pu,new = Z_pu,old · (S_new/S_old) · (V_old/V_new)²
```

# Assumptions

- Three-phase bases use line-to-line voltage.
- Change-of-base applies the impedance formula (standard machine-data
  retargeting).

# Conventions

Outputs always include the computed `impedance_base` and
`current_base` for the (old) bases, so the caller can audit the
conversion. For `operation: change_base`, the NEW base's derived
quantities are also reported as `new_impedance_base`/
`new_current_base` (`null` for `to_per_unit`/`from_per_unit`, where
there is no second base) — the new base's `Z_base`/`I_base` are what a
caller changing bases is actually trying to find, not just the old
pair.

# Applicability limits

- No sequence networks, no off-nominal turns-ratio transformers beyond
  plain base change.

# Validation rules

- Operation-specific required fields.
- `value` unit convertible to ohm/V/A/W per `quantity_kind`.
- Positive bases.

# Numerical diagnostics

`diagnostics` is always `{}`.

# Alternative methods

None within this skill.

# Failure conditions

- Missing operation fields → `INVALID`.
- Incompatible `value` unit → `INVALID`.
- Non-positive bases → `INVALID`.

# Worked examples

See `examples/`.

# References

See `references.md`.

# Known limitations

- Impedance-only change of base (not a general tensor transform).

# Changelog

- 0.1.0: initial version (Sprint 08 Fase B).
