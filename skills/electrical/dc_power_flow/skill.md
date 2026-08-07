---
id: electrical.dc_power_flow
version: 0.1.0
status: experimental
domain: electrical
title: DC Power Flow (Meshed)
---

# Purpose

Solve the canonical meshed DC linear active-power flow (plan section D4)
over a susceptance (`B`) network relative to a slack bus, and check nodal
KCL (active-power) conservation at every bus. This is a thin adapter over
`oec.physics.electrical.dc_power_flow` — the skill validates and adapts
inputs; it performs no physics arithmetic of its own.

# Problem definition

Given a set of network lines (each with a susceptance `B_ij = 1 / X_ij`,
per-unit) and one active-power injection per bus (pu, positive =
generation entering the bus), solve for the relative voltage angles
`theta_i` and line flows `P_ij = B_ij (theta_i - theta_j)`, then check
that `injection - outflow` is within tolerance at every bus.

# Supported problem classes

- Meshed (not radial-only), lossless, linear DC power flow (D4). AC power
  flow, machine models, and LP/OPF dispatch are explicitly out of scope —
  see `agent.optimization_specialist` + `optimization.lp` for optimal
  power flow / dispatch problems.

# Required inputs

- `lines` (array, >= 1 item): each `{from_bus, to_bus, susceptance > 0}`.
- `injections` (object): bus id -> active-power injection (pu, dimensionless
  per-unit — not a `QuantityValue`), one entry per bus that appears in
  `lines`, including the slack bus.
- `slack_bus` (string): must appear in `lines`' bus set.

# Optional inputs

- `atol`, `rtol` (number > 0): conservation tolerance overrides; default
  to the executed `KCL_LAW`'s defaults (`1e-9`, `1e-9`).

# Units and dimensions

Per D4, susceptances and injections are dimensionless per-unit (pu) —
this skill deliberately does not use `QuantityValue`/`x-oec-unit` for
them (ADR 0003: a `QuantityValue` never carries a fake/empty unit for a
genuinely dimensionless ratio).

# Official methodology

Reduced nodal susceptance-matrix solve (`B_reduced * theta = P_reduced`)
against every non-slack bus, then `P_ij = B_ij (theta_i - theta_j)` per
line. See `oec.physics.electrical.dc_power_flow` for the full derivation.

# Assumptions

See `DC_POWER_FLOW_ASSUMPTIONS` in `oec.physics.electrical` (mirrored
verbatim into `result.assumptions`):

- Linear network; resistive (I^2 R) losses are neglected.
- Flat voltage magnitude: |V| ~= 1 pu at every bus.
- Only active power is modeled.
- Steady-state operating point.
- The network graph is connected.
- Susceptances and injections are expressed in per-unit (pu).

# Conservation

Every nodal residual (`injection - outflow`) is produced by the executed
`KCL_LAW` (`ConservationLaw`) and aggregated via
`oec.physics.conservation.aggregate_balance` (the D5 owner) — this skill
never reimplements the tolerance check. `result.node_balance` reports one
`ConservationCheck` per bus; `result.balance` is the network-level
aggregate.

# Validation rules

Enforced by `oec.physics.electrical.dc_power_flow` itself (not a skill-local
`validation.py`): every bus in `lines` must have an injection, `slack_bus`
must be part of the topology, and the graph must be connected — a
violation raises `ElectricalNetworkError`, resulting in a failed execution.

# Failure conditions

- Empty `lines`, missing injections, unknown `slack_bus`, or a
  disconnected graph -> execution fails with a structured
  `ElectricalNetworkError`.
- A singular reduced susceptance matrix (degenerate topology) -> execution
  fails.

# Worked examples

See `examples/three_bus_balanced.json` and `tests/test_golden.py`: a
3-bus triangle network (equal susceptances) whose injections sum to zero,
hand-solved via the reduced-matrix inverse.

# References

- OEC v2.6-EXECUTION-PLAN.md, section D4.
- Wood, Wollenberg, Sheble, *Power Generation, Operation, and Control*,
  3rd ed., Chapter 4.
