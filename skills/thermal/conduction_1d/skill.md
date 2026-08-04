---
id: thermal.conduction_1d
version: 0.1.0
status: experimental
domain: thermal
title: 1D Steady Conduction
---

# Purpose

Compute the steady 1D Fourier conduction heat rate through a single path
(planar or rod) and check a steady-state thermal energy balance against
an outgoing heat rate. Thin adapter over `oec.physics.thermal` — the
skill validates and adapts inputs; it performs no physics arithmetic of
its own.

# Problem definition

`Q = k * A * (T_hot - T_cold) / L`, then check `heat_in == heat_out` at a
steady-state boundary (no transient storage term).

# Required inputs

- `conductivity` (`QuantityValue`, canonical `W / (m * K)`).
- `area` (`QuantityValue`, canonical `m ** 2`).
- `length` (`QuantityValue`, canonical `m`).
- `hot_temperature`, `cold_temperature` (`QuantityValue`, canonical `K`;
  any temperature-compatible unit, e.g. `degC`, is accepted and converted).

# Optional inputs

- `heat_out` (`QuantityValue`, canonical `W`): the heat rate leaving the
  boundary (e.g. a measured downstream heat sink). When omitted, this
  skill assumes an idealized adiabatic path with no other losses and
  defaults `heat_out` to the computed `heat_rate` itself (a trivially
  balanced check) — supply `heat_out` explicitly to exercise a real
  balance.

# Units and dimensions

All physical inputs are `QuantityValue`s (ADR 0003); `hot_temperature`
must be `>= cold_temperature` (enforced by
`oec.physics.thermal.conduction_heat_rate`, which raises `ValueError`
otherwise).

# Official methodology

`conduction_heat_rate` executes the `FOURIER_CONDUCTION_LAW`
(`PhysicalLaw`); `steady_conduction_balance` executes the
`STEADY_THERMAL_BALANCE_LAW` (`ConservationLaw`), routed through
`oec.physics.conservation` (the D5 residual owner) — never a locally
reimplemented tolerance check.

# Assumptions

See `CONDUCTION_ASSUMPTIONS` in `oec.physics.thermal`:

- 1D conduction along a single path (planar or rod).
- Steady state; no internal heat generation.
- Thermal conductivity is constant over the conduction path.

# Conservation

`result.balance` is a `ConservationCheck` (`heat_in - heat_out`, reported
in watts — the real unit of a steady thermal *rate* balance, not the
domain-wide force/power defaults blindly applied).

# Failure conditions

- `hot_temperature < cold_temperature` -> `ValueError` (execution fails).
- A temperature below absolute zero -> execution fails
  (`require_above_absolute_zero`).

# Worked examples

See `examples/planar_wall.json` and `tests/test_golden.py`: a 0.02 m
planar wall, k=1.5 W/(m*K), A=0.5 m^2, 80 degC -> 20 degC gives
Q = 2250 W exactly.

# References

- OEC v2.6-EXECUTION-PLAN.md, PHYSICS-CATALOG P2.
- Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*, 7th ed.,
  Chapter 3.
