---
id: energy.min_storage_capacity
version: 0.1.0
status: experimental
domain: energy
title: Minimum Storage Capacity (LP via optimization.lp)
---

# Purpose

Find the **minimum energy storage capacity** that serves a multiperiod
load/PV profile under **grid-zero** (no grid import), with charge/discharge
efficiencies and SOC bounds. Formulates an OPS LP and **composes**
`optimization.lp` (HiGHS).

This is **not** the same contract as `energy.grid_zero_feasibility`
(deterministic check of a *provided* trajectory).

# Official methodology

Method id: `min_storage_capacity_lp`.

Variables: `capacity`, `charge[t]`, `discharge[t]`, `grid_import[t]` (fixed 0),
`e[t]` (stored energy), optional `curtail[t]`.

# Changelog

- 0.1.0: initial (v2.6.1 Wave 2).
