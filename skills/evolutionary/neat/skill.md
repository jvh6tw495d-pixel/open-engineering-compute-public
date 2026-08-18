---
id: evolutionary.neat
version: 0.1.0
status: experimental
domain: evolutionary
title: NEAT topology evolution (neat-python)
---

# NEAT (neat-python)

Evolves network **topology and weights** under a closed fitness catalog
(`xor`, `tabular_regression`, `tabular_classification`). No caller Python
fitness. Requires `oec[evolutionary]` (ADR 0044). HyperNEAT is not included.

The result carries an OEC-owned genotype IR (nodes + connections), not a
backend genome object.
