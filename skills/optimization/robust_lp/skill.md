---
id: optimization.robust_lp
version: 0.1.0
status: experimental
domain: optimization
title: Robust LP (box RHS)
---

# Purpose

Solve a robust linear program under independent box uncertainty on selected
constraint right-hand sides (Wave C v0).

# Official methodology

Method id: `box_rhs_worst_case`. For radius δ on a constraint:
`<=` uses rhs−δ; `>=` uses rhs+δ. Equalities unsupported in v0.

# Applicability limits

- Continuous LP OPS document.
- Non-negative uncertainty radii.
- Requires HiGHS.
