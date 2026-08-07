---
id: optimization.infeasibility_explain
version: 0.2.0
status: experimental
domain: optimization
title: Infeasibility Explanation (drop-one heuristic)
---

# Purpose

Provide an **experimental heuristic** explanation of why a continuous LP is
infeasible. This skill does **not** compute a certified Irreducible
Inconsistent Subsystem (IIS).

# Official methodology

Method id: `drop_one_infeasibility_heuristic` v0.2.0.

1. Precheck bound conflicts and empty-coefficient constraints.
2. Zero-objective HiGHS solve.
3. Drop-one scan: for each constraint, remove it alone and re-solve.
   Names that restore feasibility are listed as
   ``single_constraint_relaxations``.

``claims_iis`` is always ``false``. The deprecated field
``iis_candidate_constraints`` is an alias of the same list for compatibility.

# Applicability limits

- Continuous LP OPS documents.
- Requires HiGHS.
- Budgeted number of drop-one solves (default 50).

# What not to use this for

- Claiming “the smallest” or “irreducible” conflict set.
- Production IIS extraction comparable to commercial solvers.
- MILP-grade conflict analysis.

# Changelog

- 0.2.0: honest drop-one semantics; no IIS claims without proof (A23-02).
- 0.1.0: initial Wave A.
