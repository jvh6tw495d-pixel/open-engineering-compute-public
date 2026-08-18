---
id: evolutionary.neat
version: 0.1.1
status: validated
domain: evolutionary
title: NEAT topology evolution (neat-python)
---

# NEAT (neat-python)

Evolves network **topology and weights** under a closed fitness catalog
(`xor`, `tabular_regression`, `tabular_classification`). No caller Python
fitness. Requires `oec[evolutionary]` (ADR 0044). HyperNEAT is not included.

The result carries an OEC-owned genotype IR (nodes + connections), not a
backend genome object.

# Changelog

- 0.1.1: validated — golden case requires a real genotype IR when
  `neat-python` is installed; fail-closed unit case covers the missing
  extra. HyperNEAT and caller-supplied fitness remain out of scope.
- 0.1.0: ADR 0044 initial (experimental).
