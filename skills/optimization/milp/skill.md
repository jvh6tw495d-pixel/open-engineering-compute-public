---
id: optimization.milp
version: 0.1.0
status: experimental
domain: optimization
title: Mixed-Integer Linear Program (HiGHS)
---

# Purpose

Solve a mixed-integer linear program from an OPS v0.1 document using HiGHS.

# Official methodology

Backend HiGHS (`highspy`). Requires at least one integer/binary variable.

# Numerical diagnostics

`converged` true only for optimal. Time-limit and infeasible cases set
`converged` false and populate `feasibility_issues`.

# References

https://highs.dev/ — algorithmic merit of HiGHS, not OEC.
