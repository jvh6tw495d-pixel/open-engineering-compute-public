---
id: uncertainty.lhs
version: 0.1.0
status: experimental
domain: uncertainty
title: Latin Hypercube Sample
---

# Purpose

Latin Hypercube sample design over rectangular bounds (McKay et al.).

# Official methodology

Method id: `latin_hypercube`. Stratified unit hypercube + affine map to bounds.
Deterministic when `seed` is set (ADR 0004).

# Applicability limits

- `n_samples >= 1`, each bound `low < high`.
- Design only — does not evaluate a model.

# Known limitations

- No correlation control (Iman–Conover) in Wave B.
