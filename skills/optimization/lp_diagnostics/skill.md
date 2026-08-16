---
id: optimization.lp_diagnostics
version: 0.1.0
status: experimental
domain: optimization
title: LP Diagnostics (reduced costs, slacks, duals)
---

# Purpose

Solve a continuous LP and surface its KKT report (reduced costs, per-row
slacks, dual values) for analysis. Pairs with `optimization.lp` (which
returns primal/objective/feasibility only).

# Official methodology

Method id: `highs_lp_diagnostics`. Reuses `oec.kernel.optimization.highs`
(extended in v2.3 to surface `reduced_costs` and `slacks`); no HiGHS
algorithm is reimplemented in OEC (ADR 0008).

Slack sign conventions:
- `A x <= b` → `slack = b - LHS`  (positive = inside, negative = violated)
- `A x >= b` → `slack = LHS - b`
- `A x == b` → `slack = LHS - b` (signed residual)

# Applicability limits

- `ops.problem_class == "lp"` (no MILP — mixed-integer KKT diagnostics
  are out of scope; `optimization.milp` is unaffected by this skill).

# Failure conditions

- OPS validation failure.
- OPS shape that is not LP.
- HiGHS not installed.

# Alternative methods

- `optimization.lp` for just primal/objective/feasibility without the KKT
  report.

# Known limitations

- Reduced-cost / dual extraction depends on HiGHS's internal row/column
  duals; behaviour under presolve is governed entirely by HiGHS.

# Known scope (A23-03)

This skill is **continuous LP only**. It does **not** report MIP gap,
node counts, or branch-and-bound termination statistics. Those belong
to `optimization.milp` (`mip_gap`, `mip_node_count`). Wave A “gap
reporting” language is **not** a promise of this LP diagnostics skill.

# Changelog

- 0.1.1: clarify LP-only KKT diagnostics; no MIP gap claims (A23-03).
- 0.1.0: initial (v2.3 Wave A — reduced costs / duals / slacks).
