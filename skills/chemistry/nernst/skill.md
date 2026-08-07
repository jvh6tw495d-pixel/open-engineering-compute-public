---
id: chemistry.nernst
version: 0.1.0
status: experimental
domain: chemistry
title: Nernst Cell Potential
---

# Purpose

Evaluate open-circuit cell potential via the Nernst equation.
Thin wrap over `oec.chemistry.nernst_potential`. **Not** pack/BESS SOC.

# Formula

`E = E° − (RT / nF) · ln(Q)`

# Inputs

- `e0_v` — standard potential (V)
- `n_electrons` — electrons transferred (≥ 1)
- `reaction_quotient` — dimensionless activity quotient Q (> 0)
- `temperature_k` — optional, default 298.15 K

# References

- OEC ADR 0029; V3 §12 C4
