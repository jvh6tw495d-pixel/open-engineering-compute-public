---
id: mechanics.energy_1d
version: 0.1.0
status: experimental
domain: mechanics
title: 1D Mechanical Energy Balance
---

# Purpose

Compute the kinetic and gravitational potential energy of a point mass at
an initial and final state, and check the work-energy balance between
them. Thin adapter over `oec.physics.mechanics` — the skill validates and
adapts inputs; it performs no physics arithmetic of its own (only
unit-compatible `QuantityValue` subtraction to form the deltas).

# Problem definition

`KE = 1/2 m v^2`, `PE = m g h`, and the work-energy theorem
`work_in == delta_KE + delta_PE + losses`.

# Required inputs

- `mass` (`QuantityValue`, canonical `kg`).
- `height_initial`, `height_final` (`QuantityValue`, canonical `m`).
- `velocity_initial`, `velocity_final` (`QuantityValue`, canonical `m / s`).

# Optional inputs

- `work_in` (`QuantityValue`, canonical `J`): external work done on the
  system between the two states. Defaults to `0 J`.
- `losses` (`QuantityValue`, canonical `J`): non-conservative losses
  (friction, drag, ...). Defaults to `0 J`.
- `gravity` (`QuantityValue`, canonical `m / s ** 2`): defaults to
  standard gravity (9.80665 m/s^2).

# Official methodology

`kinetic_energy` and `potential_energy` execute their respective
`PhysicalLaw`s; `mechanical_energy_balance` executes the
`MECHANICAL_ENERGY_BALANCE_LAW` (`ConservationLaw`), routed through
`oec.physics.conservation` (the D5 residual owner) in joules — the real
unit of a mechanical energy balance, not the domain-wide force default.

# Assumptions

See `ENERGY_ASSUMPTIONS` in `oec.physics.mechanics`:

- Point-mass mechanics; no rotational kinetic energy.
- Gravitational potential energy referenced to a fixed datum height.
- Non-conservative losses, if any, are supplied explicitly.

# Conservation

`result.balance` is a `ConservationCheck` on
`work_in - (delta_kinetic + delta_potential + losses)`, reported in
joules.

# Worked examples

See `examples/free_fall.json` and `tests/test_golden.py`: a 2 kg mass in
free fall from 8 m (v0=0) converts all potential energy to kinetic energy
with no external work or losses -> exactly balanced.

# References

- OEC v2.6-EXECUTION-PLAN.md, PHYSICS-CATALOG P3.
- Serway & Jewett, *Physics for Scientists and Engineers*, 9th ed.,
  Chapters 7-8.
