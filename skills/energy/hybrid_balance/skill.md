---
id: energy.hybrid_balance
version: 0.1.0
status: experimental
domain: energy
title: Hybrid Multiperiod Energy Balance
---

# Purpose

Multiperiod hybrid energy balance for a **provided** load / PV / grid /
storage trajectory. Thin adapter over `oec.physics.hybrid.hybrid_balance`.

Does **not** optimize dispatch or storage capacity (see
`energy.min_storage_capacity` and `energy.grid_zero_feasibility`).

# Official methodology

Method id: `hybrid_period_balance`.

Period residual: `load − (pv + grid_import + discharge − charge)`.
`grid_import < 0` denotes export (single-field convention).

# Changelog

- 0.1.0: initial (v2.6.1 Wave 2).
