---
id: mathematics.optimize_constrained
version: 0.1.0
status: experimental
domain: mathematics
title: Optimize Constrained
---

# Purpose

Find a local minimizer of a scalar, user-supplied objective `f(x1, ...,
xn)` of several variables, subject to optional box bounds and general
nonlinear equality/inequality constraints — using a numerically
appropriate method chosen by explicit, documented rules. Sprint 05's
second `oec.kernel.optimization` skill, extending `math.optimize_scalar`
from one variable to N and from unconstrained/box-bounded to fully
constrained.

# Problem definition

Given `f: ℝⁿ → ℝ` expressed as a mathematical expression string in `n`
named variables, find `x* ∈ ℝⁿ` that minimizes `f`, starting from a
caller-given initial guess `x0`, subject to optional box bounds per
variable and optional nonlinear constraints `g(x) = 0` (equality) or
`g(x) ≥ 0` (inequality, SciPy's own sign convention). To maximize `f`,
minimize `-f` — no separate maximize mode, matching `optimize_scalar`.

# Supported problem classes

- **Unconstrained**: no `bounds`, no `constraints` — reduces to plain
  multi-variable minimization from `x0`.
- **Box-bounded**: `bounds` given, no `constraints`.
- **Nonlinearly constrained**: any number of `constraints` (equality
  and/or inequality), with or without `bounds`.

# Required inputs

- `variables` (array of strings, non-empty, no duplicates): the decision
  variable names, in order. Referenced by `expression` and every
  `constraints[].expression`.
- `expression` (string): `f(variables...)`, using only the names in
  `variables` plus the restricted-grammar functions/constants shared
  with every other math skill (arithmetic,
  `sin/cos/tan/asin/acos/atan/sinh/cosh/tanh/exp/log/log10/log2/sqrt/abs`,
  `pi`/`e`). Parsed by
  `oec.kernel.numerics.expressions.compile_expression_vector` — the
  N-variable generalization of the single-variable evaluator
  `mathematics.solve_root`/`mathematics.optimize_scalar` use.
- `x0` (array of numbers, same length as `variables`): initial guess.

# Optional inputs

- `bounds` (array of `[lo, hi]` pairs, same length/order as
  `variables`; either side may be `null` for unbounded in that
  direction).
- `constraints` (array of `{type: "eq"|"ineq", expression: string}`):
  `type: "eq"` means `expression(variables...) == 0`; `type: "ineq"`
  means `expression(variables...) >= 0` (SciPy's own sign convention —
  a constraint written as `x <= 5` must be given as the expression
  `5 - x`, not `x - 5`).
- `method` (string, one of `SLSQP`/`trust-constr`): if omitted, selected
  by the rule in "Official methodology" below.
- `tolerance` (number, > 0): passed to SciPy as `tol`.
- `max_iterations` (integer, > 0): iteration cap.

# Units and dimensions

Dimensionless by design, matching every other `mathematics.*` MVP
skill. Non-dimensionalize a physically-dimensioned problem before
calling this skill.

# Official methodology

Method selection is explicit and documented, never inferred silently
(plan section 4.4): **`SLSQP` is always the default**, regardless of
whether `bounds`/`constraints` are present — it handles the
unconstrained, box-bounded, and fully-constrained cases uniformly, and
is SciPy's traditional workhorse for this problem class. `trust-constr`
is available as an explicit alternative — pick it when you specifically
want its native `optimality`/`constraint_violation` diagnostics (see
"Numerical diagnostics" below); it is never auto-selected.

# Mathematical formulation

- **SLSQP** (Sequential Least Squares Programming): solves a sequence of
  quadratic-programming subproblems that locally approximate the
  Lagrangian, handling bounds and general nonlinear constraints
  together (Nocedal & Wright, Ch. 18).
- **trust-constr**: an interior-point / trust-region method for
  constrained optimization; more expensive per iteration than SLSQP but
  reports richer native convergence diagnostics (`optimality`,
  `constr_violation`) that SLSQP does not compute at all.

# Assumptions

- `f` and every constraint are real-valued and continuous in the
  relevant neighborhood.
- **The result is a local minimum, not necessarily the global one** —
  same caveat as `mathematics.optimize_scalar`, now in N dimensions:
  both SLSQP and trust-constr descend from `x0` toward the nearest
  local minimum. A non-convex objective can have several local minima;
  see "Worked examples" for Himmelblau's function, a well-known
  four-minima test case, demonstrating that which minimum is found
  depends entirely on `x0`.
- Constraint feasibility at the *initial* point `x0` is not required —
  SLSQP/trust-constr can start infeasible and search toward
  feasibility — but a problem whose constraints are mutually
  contradictory (no feasible point exists at all) will not converge to
  a feasible point; see "Failure conditions".

# Conventions

Variable names are whatever the caller declares in `variables` — unlike
`mathematics.solve_root`/`mathematics.optimize_scalar` (which hardcode
`x`), this skill has no fixed single-variable convention since it
operates on `n ≥ 1` named variables.

# Applicability limits

- No integer/mixed-integer variables — every entry of `x0` and the
  result `x` is a continuous real.
- No maximize mode: minimize `-f(variables...)` and negate `fun`.
- `max_iterations` bounds the search; exhausting it returns
  `diagnostics.converged = false` (see "Failure conditions"), not an
  error.

# Validation rules

Implemented in `validation.py` (`OptimizeConstrainedValidator`, layer
`mathematical`), run before execution:

- `variables` must have no duplicate names (schema-level `minItems`/
  `required` already covers non-empty/presence).
- `x0` must have the same length as `variables`.
- If `bounds` is given: same length as `variables`; each pair with both
  sides non-null must have `lo < hi`.
- `expression` and every `constraints[].expression` must parse under
  the restricted-AST grammar against exactly the declared `variables`
  names — an unknown name (including a typo, or a name not in
  `variables`) is an `ERROR`-severity outcome, not a crash.

The JSON Schema layer (`input.schema.json`) separately enforces types,
array shapes, `tolerance > 0`, `max_iterations > 0`, `constraints[].type
∈ {eq, ineq}`, and rejects unknown top-level properties.

# Numerical diagnostics

`diagnostics` always contains: `method`, `converged` (bool —
**required**, per ADR 0013, since this skill's method is always
iterative), `message` (SciPy's own termination message),
`n_iterations`, `n_function_evaluations`. Additionally, from the shared
`OptimizationDiagnostics` contract:

- `optimality`: `trust-constr`'s native gradient-optimality measure.
  **`None` for SLSQP** — SciPy's SLSQP result does not compute this at
  all; it is not fabricated.
- `constraint_violation` / `feasible`: for `trust-constr`, SciPy's own
  native `constr_violation`. For SLSQP (which reports nothing of the
  kind), this skill evaluates every constraint at the returned solution
  itself and reports the worst violation (`0` for a satisfied
  inequality, `|g(x)|` for an equality, `max(0, -g(x))` for an
  unsatisfied inequality) — `feasible` is `true` iff that worst
  violation is `≤ 1e-6`. With *no* constraints at all, SLSQP reports
  `(None, None)` (nothing was ever measured), while trust-constr's own
  `constr_violation` of `0.0` is still reported as `feasible: true` —
  each reflects what that specific method actually computed, not a
  fabricated agreement between the two.
- `residuals` / `covariance`: always `None` here — these belong to
  least-squares curve fitting (`mathematics.curve_fit`), not general
  constrained minimization.

# Alternative methods

- `trust-constr` over `SLSQP` when the native `optimality`/
  `constraint_violation` diagnostics matter more than raw speed, or
  when a problem has many constraints (trust-constr's interior-point
  approach tends to scale better).
- `mathematics.optimize_scalar` remains the right tool for pure
  single-variable, box-bounded-only problems — simpler, and does not
  require a `variables` array of length 1.

# Failure conditions

- `expression`/`constraints[].expression` fails to parse or references
  an unknown name → `INVALID` (validation layer, execution never runs).
- `x0`/`bounds` length mismatch with `variables`, or a degenerate bound
  pair (`lo >= hi`) → `INVALID`.
- Duplicate names in `variables` → `INVALID`.
- Mutually contradictory constraints (no feasible point exists) →
  `diagnostics.converged = false` and/or `diagnostics.feasible = false`
  — not an error; the returned `x`/`fun` are the solver's last iterate,
  not a trustworthy result. See "Worked examples" for a concrete case.
- Iteration budget exhausted without convergence →
  `diagnostics.converged = false`, status `INCONCLUSIVE` (ADR 0007).

# Worked examples

**Unconstrained**: `{"variables": ["x","y"], "expression": "x**2 + y**2", "x0": [1, 1]}`
→ `{"x": [0.0, 0.0], "fun": 0.0, "method": "SLSQP", ...}` (trivially
independently known global minimum).

**Constrained** (classic textbook case): minimize `x² + y²` subject to
`x + y ≥ 1` → `x* = (0.5, 0.5)`, `fun = 0.5` — derivable independently
via Lagrange multipliers (by symmetry of the objective and the active
constraint boundary `x+y=1`).

**Multi-minima** (Himmelblau's function, `f(x,y) = (x²+y-11)² +
(x+y²-7)²`): has four known global minima, all with `fun = 0`, at
`(3, 2)`, `(-2.805118, 3.131312)`, `(-3.779310, -3.283186)`,
`(3.584428, -1.848126)` (Himmelblau, 1972 — independent of this skill,
a standard textbook test function). `x0 = [3, 2]` converges to the
first exactly; `x0 = [-2.8, 3.1]` converges to the second — same
objective, different `x0`, different minimum found.

**Infeasible**: constraints `x + y ≤ 0` (as `-(x+y) ≥ 0`) and
`x + y ≥ 1` simultaneously — no point can satisfy both. SLSQP returns
`diagnostics.converged = false`, `diagnostics.feasible = false`,
`diagnostics.constraint_violation = 1.0` (the two constraints disagree
by exactly `1` in this construction) — a diagnostic outcome, not a
crash.

See `examples/` for the full request/response pairs used in
`tests/test_golden.py`.

# References

- Nocedal, J., Wright, S. J. (2006). *Numerical Optimization*, 2nd ed.,
  Springer, Chapter 18 (SQP methods).
- Himmelblau, D. M. (1972). *Applied Nonlinear Programming*.
  McGraw-Hill — source of the four-minima test function.
- SciPy documentation: `scipy.optimize.minimize` (`method='SLSQP'`,
  `method='trust-constr'`).

# Known limitations

- No global-optimization guarantee — see "Assumptions".
- No maximize mode.
- No integer/mixed-integer variables.
- `optimality` is always `None` under SLSQP (not computed by that
  method) — use `trust-constr` if that diagnostic is required.

# Changelog

- 0.1.0: initial version. Sprint 05, Fase B; second consumer of
  `oec.kernel.optimization`'s shared `OptimizationDiagnostics` contract.
