---
id: electrical.power_factor_correction
version: 0.1.0
status: experimental
domain: electrical
title: Power Factor Correction
---

# Purpose

Size a capacitor bank that raises a lagging load's displacement power
factor from an existing value to a desired higher value, returning the
reactive-power balance and the capacitance per capacitor unit for
single-phase, three-phase delta, or three-phase star connections.

# Problem definition

Given active power `P`, existing PF, desired PF, system voltage,
frequency, and bank connection, compute `Q_existing`, `Q_desired`,
`Q_capacitor = Q_existing − Q_desired`, and `C` per unit.

# Supported problem classes

- Single-phase capacitor across the load voltage.
- Three-phase delta bank (each unit sees `V_LL`).
- Three-phase star bank (total reactive identity `Q = ω C V_LL²`).

# Required inputs

- `active_power` (`QuantityValue`, `x-oec-unit: "W"`).
- `existing_power_factor` (number, `0 < PF ≤ 1`).
- `desired_power_factor` (number, `0 < PF ≤ 1`, must be `≥ existing`).
- `voltage` (`QuantityValue`, `x-oec-unit: "V"`).
- `frequency` (`QuantityValue`, `x-oec-unit: "Hz"`).
- `phase_count` (`1` | `3`).
- `connection` (`single_phase` | `delta` | `star`).

# Optional inputs

None.

# Units and dimensions

Canonical conversion via ADR 0016. Reactive-power outputs use unit
label `var` (defined on the shared Pint registry as dimensionally equal
to watt). Capacitance is reported in `uF`.

# Official methodology

Closed-form reactive-power triangle correction; no solver.

# Mathematical formulation

```
Q_existing = P · tan(acos(PF_existing))
Q_desired  = P · tan(acos(PF_desired))
Q_c        = Q_existing − Q_desired
ω          = 2 π f
```

```
single_phase / star:  C = Q_c / (ω V²)
delta:                C = Q_c / (3 ω V_LL²)
```

`C` is the capacitance of **each** unit in the bank.

# Assumptions

- Load is lagging both before and after correction.
- Displacement PF only (no harmonics).
- Ideal capacitors; no detuning reactors.

# Conventions

Three-phase `voltage` is line-to-line. `desired_power_factor` must not
be lower than `existing` — this skill only sizes raise-PF banks.

# Applicability limits

- No automatic switching / multi-step banks.
- No overvoltage or resonance study.

# Validation rules

- `phase_count` ↔ `connection` consistency.
- `desired_power_factor ≥ existing_power_factor`.
- Positivity of power, voltage, frequency.

# Numerical diagnostics

`diagnostics` is always `{}`.

# Alternative methods

Synchronous-condenser sizing or harmonic-filtered banks would be
separate skills.

# Failure conditions

- Inconsistent connection/phase_count → `INVALID`.
- Desired PF below existing → `INVALID`.
- Non-positive physical inputs → `INVALID`.

# Worked examples

See `examples/`.

# References

See `references.md`.

# Known limitations

- Displacement PF only.
- No temperature or tolerance derating of C.

# Changelog

- 0.1.0: initial version (Sprint 09).
