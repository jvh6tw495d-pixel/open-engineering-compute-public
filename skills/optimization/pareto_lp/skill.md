---
id: optimization.pareto_lp
version: 0.1.0
status: experimental
domain: optimization
title: Bi-objective LP Pareto (weighted sum)
---

# Purpose

Approximate a bi-objective Pareto set for a linear program by sweeping
convex combination weights of two linear objectives (Wave C v0).

# Official methodology

Method id: `pareto_weighted_sum`. For weights w on a uniform grid,
solve LP with combined objective `w c_a + (1-w) c_b`, then filter
non-dominated points under the base OPS sense.

# Applicability limits

- Continuous LP only (`problem_class=lp`).
- Two objectives; n_points >= 2.
- Requires HiGHS (`oec[optimization]`).

# Known limitations

- Weighted-sum only finds supported efficient points.
