---
id: electrical.three_phase_power
version: 0.1.0
status: experimental
domain: electrical
title: Three-Phase Power
---

# Purpose

Compute active, reactive, and apparent power for a **balanced**
three-phase electrical system from its line-to-line voltage, line
current, and power factor. OEC's first electrical skill (Sprint 08) and
the template every later electrical skill's package layout is copied
from — the first to declare `QuantityValue`-shaped, dimensional inputs
converted through the central normalization pipeline
(`docs/architecture/adr/0016-central-dimensional-normalization.md`).

# Problem definition

Given a balanced three-phase system's RMS line-to-line voltage `V_LL`,
RMS line current `I_L`, and power factor `PF = cos(φ)`, compute the
apparent power `S`, active power `P`, and reactive power `Q` the system
draws.

# Supported problem classes

- **Balanced three-phase load**, any connection (star or delta) — the
  line-to-line voltage / line current convention this skill uses is
  connection-agnostic by construction (see "Mathematical formulation").
- **Lagging (inductive) or leading (capacitive) loads**, distinguished
  by `power_factor_type`, which determines the sign of `reactive_power`.

Unbalanced three-phase systems are explicitly out of scope — see
"Applicability limits".

# Required inputs

- `voltage_line_to_line` (`QuantityValue`, `x-oec-unit: "V"`): RMS
  line-to-line (phase-to-phase) voltage.
- `current_line` (`QuantityValue`, `x-oec-unit: "A"`): RMS line current.
- `power_factor` (number, `0 <= PF <= 1`): `cos(φ)` magnitude. Direction
  (lagging/leading) is given separately — see `power_factor_type`.

# Optional inputs

- `power_factor_type` (string, one of `lagging`/`leading`): whether the
  load is inductive (`lagging`, the common case — motors, transformers)
  or capacitive (`leading`). Determines the **sign** of
  `reactive_power`, not its magnitude. Defaults to `lagging`.

# Units and dimensions

`voltage_line_to_line` and `current_line` are `QuantityValue`s,
converted to their canonical unit (`V`, `A`) by `ExecutionService`
before this skill's implementation ever runs (ADR 0016) — any
dimensionally-compatible unit the caller submits (`kV`, `mA`, ...) is
accepted and normalized first. `power_factor` is dimensionless (a
ratio) and is never wrapped as a `QuantityValue`, per ADR 0003's
consequence that dimensionless ratios stay plain numbers.

# Official methodology

There is exactly one formula path — no method selection, no solver.
This is closed-form arithmetic (`method.iterative: false`); a valid
input always produces a result, and `ExecutionStatus.VERIFIED` (not
`VALIDATED`) reflects that there is no convergence concept to satisfy.

# Mathematical formulation

For a balanced three-phase system, using the line-to-line voltage and
line current convention (valid for both star and delta connections —
the `sqrt(3)` factor is exactly what converts a single-phase-style
`V*I` product into the three-phase total, regardless of how the load is
internally connected):

```
S = sqrt(3) * V_LL * I_L                     (apparent power, VA)
P = S * PF                                    (active power, W)
Q = S * sin(acos(PF))                         (reactive power magnitude, var)
```

`reactive_power`'s **sign** follows `power_factor_type`: positive for
`lagging` (the load absorbs reactive power — inductive convention),
negative for `leading` (the load supplies reactive power — capacitive
convention). This is the standard IEEE sign convention for reactive
power (references.md #3).

The power triangle identity `S^2 = P^2 + Q^2` holds for every valid
input by construction — verified as a property test
(`tests/test_properties.py`), not merely for the worked examples.

# Assumptions

- The system is **balanced**: all three phases carry equal-magnitude
  currents at 120° mutual displacement, and line-to-line voltages are
  equal in magnitude. An unbalanced system's real power draw is not
  computable from a single `(V_LL, I_L, PF)` triple.
- `voltage_line_to_line` and `current_line` are RMS values, not peak.
- `power_factor` is the true (displacement) power factor — harmonic
  distortion's contribution to a "true power factor" that differs from
  `cos(φ)` is out of scope.

# Conventions

Line-to-line voltage and line current (not phase quantities) are the
required input shape — the most common way three-phase quantities are
measured and specified on equipment nameplates and single-line
diagrams. A caller with phase (line-to-neutral) voltage for a
star-connected system must convert (`V_LL = sqrt(3) * V_phase`) before
calling this skill; that conversion is not performed here.

# Applicability limits

- Balanced systems only (see "Assumptions") — no per-phase unbalance
  input, no negative/zero-sequence decomposition.
- No harmonic content — `power_factor` is treated as the pure
  displacement power factor.
- `power_factor` domain is `[0, 1]`; a `power_factor` of exactly `0`
  (purely reactive load, `P = 0`) is valid, not rejected.

# Validation rules

Implemented in `validation.py` (`ThreePhasePowerValidator`, layer
`physical`), run before execution, using `oec.validation.physical`'s
shared `require_positive` helper:

- `voltage_line_to_line.value` must be strictly positive (a zero or
  negative voltage magnitude is not a real system).
- `current_line.value` must be strictly positive.

The JSON Schema layer separately enforces types, required keys, and
`0 <= power_factor <= 1`. The dimensional layer
(`DimensionalValidator`) separately enforces that submitted units are
convertible to `V`/`A` — see ADR 0016.

# Numerical diagnostics

`diagnostics` is always `{}` — an exact closed-form computation has no
convergence, iteration count, or residual to report (ADR 0013 only
requires `converged` from methods that declare `iterative: true`; this
one doesn't).

# Alternative methods

There is no alternative method for this problem class within this
skill — a future `electrical.three_phase_power_unbalanced` skill (not
in this MVP) would be the right place for symmetrical-components-based
unbalanced analysis, out of scope here by design.

# Failure conditions

- `voltage_line_to_line` or `current_line` not positive → `INVALID`.
- `voltage_line_to_line`/`current_line` unit dimensionally incompatible
  with `V`/`A` (e.g. submitting `10 W` as a voltage) → `INVALID`.
- `power_factor` outside `[0, 1]` → `INVALID` (schema layer).
- There is no `FAILED`/`INCONCLUSIVE` path: a valid input to this exact
  formula cannot fail to produce a finite result.

# Worked examples

`{"voltage_line_to_line": {"value": 380, "unit": "V"}, "current_line":
{"value": 10, "unit": "A"}, "power_factor": 0.8, "power_factor_type":
"lagging"}` →
`{"active_power": {"value": 5265.43..., "unit": "W"}, "reactive_power":
{"value": 3949.08..., "unit": "var"}, "apparent_power": {"value":
6581.79..., "unit": "VA"}}`.

See `examples/` for the full request/response pairs used in
`tests/test_golden.py`.

# References

See `references.md`.

# Known limitations

- No unbalanced-system support (see "Applicability limits").
- No harmonic/true-power-factor distinction.
- No phase-voltage input shape (line-to-line only).

# Changelog

- 0.1.0: initial version. First electrical skill (Sprint 08); the first
  to exercise ADR 0016's central dimensional normalization end-to-end.
