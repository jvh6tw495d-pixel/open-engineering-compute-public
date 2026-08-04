---
id: fluids.bernoulli
version: 0.1.0
status: experimental
domain: fluids
title: Bernoulli Head Balance with Friction Losses
---

# Purpose

Compute the Bernoulli head at an upstream and a downstream section of a
pipe, the Darcy-Weisbach friction head loss between them, and check the
head balance `H_upstream == H_downstream + h_loss`. Thin adapter over
`oec.physics.fluids` — the skill validates and adapts inputs; it
performs no physics arithmetic of its own.

# Problem definition

`H = p/(rho g) + v^2/(2g) + z` at each section; friction loss
`h_L = f (L/D) v^2/(2g)` using the upstream velocity as the pipe's
characteristic velocity (constant-diameter, fully-developed flow); then
check `H_upstream == H_downstream + h_loss`.

# Required inputs

- `pressure_upstream`, `pressure_downstream` (`QuantityValue`, canonical `Pa`).
- `velocity_upstream`, `velocity_downstream` (`QuantityValue`, canonical `m / s`).
- `elevation_upstream`, `elevation_downstream` (`QuantityValue`, canonical `m`).
- `density` (`QuantityValue`, canonical `kg / m ** 3`).
- `friction_factor` (number, dimensionless >= 0): the Darcy friction
  factor `f`, supplied directly as an **input** — this skill never
  derives it from Reynolds number, pipe roughness, or a Colebrook-type
  correlation (out of scope for v0, per `oec.physics.fluids`).
- `length` (`QuantityValue`, canonical `m`): pipe length between sections.
- `diameter` (`QuantityValue`, canonical `m`): pipe diameter.

# Optional inputs

- `gravity` (`QuantityValue`, canonical `m / s ** 2`): defaults to
  standard gravity (9.80665 m/s^2).

# Official methodology

`bernoulli_head` and `darcy_weisbach_head_loss` execute their respective
`PhysicalLaw`s; `bernoulli_balance` executes the `BERNOULLI_BALANCE_LAW`
(`ConservationLaw`), routed through `oec.physics.conservation` (the D5
residual owner), reported in meters of head.

# Assumptions

See `BERNOULLI_ASSUMPTIONS` + `LOSSES_ASSUMPTIONS` in
`oec.physics.fluids`:

- Incompressible, inviscid flow along a single streamline (ideal
  Bernoulli term); steady flow.
- Darcy friction factor `f` is supplied as an input; no Reynolds/Colebrook
  regime determination is performed.
- Fully-developed flow in a straight pipe of constant diameter.

# Conservation

`result.balance` is a `ConservationCheck` on
`head_upstream - head_downstream - head_loss`, reported in meters.

# Worked examples

See `examples/pipe_run.json` and `tests/test_golden.py`: equal velocity
and elevation upstream/downstream, with the pressure drop chosen to
exactly match the computed Darcy-Weisbach loss.

# References

- OEC v2.6-EXECUTION-PLAN.md, PHYSICS-CATALOG P4.
- White, F. M., *Fluid Mechanics*, 8th ed., Chapters 3 and 6.
