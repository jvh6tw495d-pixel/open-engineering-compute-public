---
id: numerical.pde_1d_heat
version: 0.1.0
status: experimental
domain: numerical
title: 1D Heat / Poisson PDE (FDM foundation)
---

# Purpose

Foundational 1D heat / Poisson solver on a uniform grid with Dirichlet
boundaries (W1). Modes: `steady` (second-order FDM for `-u'' = source`) and
`transient` (explicit FTCS with CFL check).

Not industrial FEM/CFD.

# Official methodology

Method id: `fdm_heat_1d`.

# Changelog

- 0.1.0: W1-MVP initial.
