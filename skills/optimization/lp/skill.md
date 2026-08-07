---
id: optimization.lp
version: 0.1.0
status: experimental
domain: optimization
title: Linear Program (HiGHS)
---

# Purpose

Solve a continuous linear program given as an **OEC Problem Specification
(OPS) v0.1** document, using **HiGHS** as the numerical engine.

# Problem definition

Minimize or maximize a linear objective over continuous variables subject
to linear equality/inequality constraints.

# Official methodology

- Backend: HiGHS (`highspy`), optional extra `oec[optimization]`.
- Input language: OPS — no arbitrary Python.
- Method id: `highs_lp`.

# Assumptions

- All variables continuous (`problem_class: lp`).
- Linear objective and constraints only.

# Numerical diagnostics

`diagnostics.converged` is true iff HiGHS returns optimal.

# References

See `references.md`. HiGHS owns the algorithmic merit.

# Changelog

- 0.1.0: initial Phase C skill.
