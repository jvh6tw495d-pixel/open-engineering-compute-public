---
id: evolutionary.hyperneat
version: 0.2.0
status: validated
domain: evolutionary
title: HyperNEAT / ES-HyperNEAT (CPPN + closed substrate)
---

# HyperNEAT (neat-python CPPN + OEC substrate)

Evolves a CPPN with NEAT; the CPPN queries a closed substrate to express
connection weights. Substrates: `layered_1d` (ADR 0045) or `es_quadtree`
(ADR 0048, bounded ES-HyperNEAT). Fitness catalog is the same as
`evolutionary.neat` (`xor`, `tabular_regression`, `tabular_classification`).
Requires `oec[evolutionary]`. TITAN is not used.

The result carries an OEC-owned CPPN genotype IR plus the expressed
substrate (coordinates and weights).
