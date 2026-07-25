---
id: electrical.current_from_power
version: 0.1.0
status: experimental
domain: electrical
title: Current From Power
---

# Purpose

Compute the current a single-phase or (balanced) three-phase load
draws, given its active or apparent power, system voltage, and (for
active power) power factor — with an optional efficiency correction for
loads whose *useful* power output differs from the electrical power
they actually draw (e.g. a motor's mechanical output vs. its electrical
input).

# Problem definition

Given power `power` (active or apparent, `power_type` says which),
system voltage `voltage`, phase count, and — when `power_type` is
`active` — power factor `PF`, compute the current `I` the system draws.

# Supported problem classes

- **Single-phase, active power**: `I = (power/efficiency) / (V * PF)`.
- **Single-phase, apparent power**: `I = (power/efficiency) / V`.
- **Three-phase, active power** (balanced, line-to-line voltage/line
  current convention): `I = (power/efficiency) / (sqrt(3) * V_LL * PF)`.
- **Three-phase, apparent power**: `I = (power/efficiency) / (sqrt(3) * V_LL)`.

# Required inputs

- `power` (`QuantityValue`, `x-oec-unit: "W"`): active or apparent
  power — which one is declared by `power_type`. `W` and `VA` are
  dimensionally identical in the underlying units engine (Pint), so
  either unit (or `kW`/`kVA`, ...) is accepted for either
  `power_type`; the **label carries the engineering meaning**, the
  units engine only carries the magnitude.
- `power_type` (string, one of `active`/`apparent`).
- `voltage` (`QuantityValue`, `x-oec-unit: "V"`): single-phase system
  voltage, or three-phase line-to-line voltage.
- `phase_count` (integer, `1` or `3`).

Conditionally required:

- `power_factor` (number, `0 <= PF <= 1`): required when `power_type`
  is `active`; **rejected** (not silently ignored) when `power_type`
  is `apparent` — apparent power alone already fixes the current, so a
  supplied `power_factor` would either be redundant or, worse, a
  caller's mistaken belief that it changes the answer.

# Optional inputs

- `efficiency` (number, `0 < efficiency <= 1`, default `1.0`): divides
  `power` to obtain the actual electrical power drawn from the supply.
  Models a lossy load (e.g. a motor) whose nameplate/rated `power` is
  its *useful output*, not its electrical input.

# Units and dimensions

`power` and `voltage` are converted to their canonical unit (`W`, `V`)
by `ExecutionService` before this skill's implementation ever runs
(ADR 0016). `power_factor` and `efficiency` are dimensionless ratios,
never wrapped as `QuantityValue`s.

# Official methodology

No method selection — one formula per `(phase_count, power_type)`
combination, chosen deterministically from the inputs, never inferred
beyond what's given. See "Supported problem classes".

# Mathematical formulation

Let `P_elec = power / efficiency` (the actual electrical power drawn).

```
Single-phase: I = P_elec / (V * PF)          if power_type = active
              I = P_elec / V                  if power_type = apparent
Three-phase:  I = P_elec / (sqrt(3) * V_LL * PF)   if power_type = active
              I = P_elec / (sqrt(3) * V_LL)         if power_type = apparent
```

These follow directly from `S = V*I` (single-phase) or
`S = sqrt(3)*V_LL*I_L` (three-phase) — see
`electrical.three_phase_power`'s "Mathematical formulation" for the
three-phase identity's derivation — combined with `P = S * PF`.

# Assumptions

- Three-phase systems are balanced (same assumption as
  `electrical.three_phase_power`).
- `power_factor` is the true (displacement) power factor.
- `efficiency`, when given, is constant (not load- or
  temperature-dependent) over the operating point being evaluated.

# Conventions

Three-phase `voltage` is always line-to-line; the computed current for
`phase_count: 3` is always line current — same convention as
`electrical.three_phase_power`, for consistency across the electrical
skill family.

# Applicability limits

- Balanced three-phase only.
- `efficiency` applies uniformly regardless of `power_type` — there is
  no separate "input vs. output" distinction for apparent power (which
  has no independent mechanical/electrical duality the way active
  power of a motor does); it is provided for generality, not a
  claim that it is physically meaningful in every apparent-power case.

# Validation rules

Implemented in `validation.py` (`CurrentFromPowerValidator`, layer
`physical`):

- `power_type: active` requires `power_factor`; `power_type: apparent`
  rejects it (cross-field presence rule, mirrors
  `mathematics.solve_root`'s `method`/`bracket` pattern).
- `power.value` and `voltage.value` must be strictly positive
  (`oec.validation.physical.require_positive`).

The JSON Schema layer separately enforces types, required keys, and
`power_factor`/`efficiency` ranges. The dimensional layer separately
enforces unit compatibility with `W`/`V`.

# Numerical diagnostics

`diagnostics` is always `{}` — exact closed-form computation, no
convergence concept (`method.iterative: false`).

# Alternative methods

None within this skill's scope — see `electrical.three_phase_power`'s
"Alternative methods" for the same reasoning (an unbalanced-system
variant would be a separate future skill).

# Failure conditions

- `power_type: active` without `power_factor`, or `power_type:
  apparent` with `power_factor` → `INVALID`.
- `power` or `voltage` not positive → `INVALID`.
- `power`/`voltage` unit dimensionally incompatible with `W`/`V` →
  `INVALID`.
- No `FAILED`/`INCONCLUSIVE` path — a valid input to this exact formula
  always produces a finite result.

# Worked examples

`{"power": {"value": 1000, "unit": "W"}, "power_type": "active",
"voltage": {"value": 230, "unit": "V"}, "phase_count": 1,
"power_factor": 0.8}` → `{"current": {"value": 5.4347..., "unit":
"A"}, ...}`.

See `examples/` for the full request/response pairs used in
`tests/test_golden.py`.

# References

See `references.md`.

# Known limitations

- No unbalanced three-phase support.
- No harmonic/true-power-factor distinction.
- `efficiency` is a single scalar, not a load-dependent curve.

# Changelog

- 0.1.0: initial version.
