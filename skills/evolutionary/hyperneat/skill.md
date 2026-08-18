---
id: evolutionary.hyperneat
version: 0.1.0
status: validated
domain: evolutionary
title: HyperNEAT (CPPN + fixed substrate)
---

# HyperNEAT (neat-python CPPN + OEC substrate)

Evolves a CPPN with NEAT; the CPPN queries a closed `layered_1d` substrate
to express connection weights. Fitness catalog is the same as
`evolutionary.neat` (`xor`, `tabular_regression`, `tabular_classification`).
Requires `oec[evolutionary]` (ADR 0045). ES-HyperNEAT is not included.

The result carries an OEC-owned CPPN genotype IR plus the expressed
substrate (coordinates and weights).
