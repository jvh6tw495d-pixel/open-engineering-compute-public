---
id: energy.grid_zero_feasibility
version: 0.1.0
status: experimental
domain: energy
title: Grid-Zero Feasibility (Provided Trajectory)
---

# Purpose

Deterministic evaluation of a **provided** multiperiod trajectory for
grid-zero operation (no positive grid import). Thin adapter over
`oec.physics.grid_zero.grid_zero_feasibility`.

**No** LP, **no** HiGHS, **no** capacity minimization. For optimal sizing
see `energy.min_storage_capacity`.

# Official methodology

Method id: `grid_zero_trajectory_check`.

# Changelog

- 0.1.0: initial (v2.6.1 Wave 2).
