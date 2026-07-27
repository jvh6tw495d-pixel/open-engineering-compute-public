---
id: optimization.infeasibility_explain
version: 0.1.0
status: experimental
domain: optimization
title: Infeasibility Explanation (Lite IIS)
---

# Purpose

Explain why a linear model is infeasible. Three explanation tiers, returned
in order from which less-costly remediation is more likely:

1. **Tier `precheck`** — bound conflicts (`lower > upper` for a variable)
   or no-coefficient constraints make the model infeasible without solving.
2. **Tier `iis_candidate`** — drop-one sensitivity scan that reports the
   smallest set of constraints whose removal restores feasibility
   (a candidate irreducible inconsistent subsystem).
3. **Tier `feasible`** — the model is actually feasible; the explanation
   confirms the pre-check saw no issue.

# Official methodology

Method id: `highs_infeasibility_explain`. Reuses
`oec.kernel.optimization.highs` for the feasibility-only solve; no
algorithm is reimplemented in OEC (ADR 0008). The IIS scan is a basic
drop-one iteration, NOT a full LP-IIS extraction; a production-quality
path (`Chinneck 2008`) is a v2.4 candidate.

# Applicability limits

- `ops.problem_class == "lp"` (MILP-grade IIS extraction is out of scope).
- Up to ~30 constraints for the drop-one scan (the heuristic's cost grows
  linearly — HiGHS calls = number of constraints, so v0 ceilings at small
  scale).

# Failure conditions

- OPS validation failure.
- Non-LP class.
- HiGHS not installed.

# Alternative methods

- `optimization.check_feasibility` for a one-bit feasibility verdict
  without the human-readable explanation.

# Known limitations

- The drop-one IIS scan is **O(n)** HiGHS solves, not the polynomial-time
  IIS extraction in commercial solvers. A binary/on-off relaxation
  (Chinneck §8) is a v2.4 candidate.

# Changelog

- 0.1.0: initial (v2.3 Wave A — infeasibility explain enrichment).