---
id: mathematics.curve_fit
version: 0.1.0
status: experimental
domain: mathematics
title: Curve Fit
---

# Purpose

Fit a user-supplied parametric model `y = f(x; p1, ..., pn)` to observed
`(x, y)` data by nonlinear least squares, using a numerically
appropriate method chosen by explicit, documented rules. Sprint 05's
third `oec.kernel.optimization` skill: reuses the shared
`OptimizationDiagnostics` contract's `residuals`/`covariance` fields,
which `optimize_scalar`/`optimize_constrained` never set.

# Problem definition

Given data `(xᵢ, yᵢ)`, `i = 1..m`, and a model `f(x; p)` with `p ∈ ℝⁿ`,
find `p*` minimizing `Σᵢ (yᵢ - f(xᵢ; p*))²` — ordinary (unweighted)
nonlinear least squares. There is no support for per-point weighting
(`sigma` in SciPy's terms) in this MVP — see "Known limitations".

# Supported problem classes

- **Unconstrained nonlinear least squares**: no `bounds` given; solved
  by Levenberg-Marquardt (`lm`).
- **Bounded nonlinear least squares**: `bounds` given on some or all
  parameters; solved by Trust Region Reflective (`trf`, the default
  bounded method) or `dogbox` if explicitly requested.

See "Official methodology" below for the exact `lm`/`trf`/`dogbox`
selection rule.

# Required inputs

- `model` (string): `f(x; parameter_names...)`. The independent
  variable is **always** named `x` (matching every other math skill's
  fixed-name convention); `parameter_names` supplies the rest of the
  symbols. Parsed by
  `oec.kernel.numerics.expressions.compile_expression_vector` — same
  restricted grammar as every other math skill (arithmetic,
  `sin/cos/tan/asin/acos/atan/sinh/cosh/tanh/exp/log/log10/log2/sqrt/abs`,
  `pi`/`e`).
- `parameter_names` (array of strings, non-empty, no duplicates, must
  not contain `"x"`): the free parameters to fit, in order.
- `x` (array of numbers): independent-variable data.
- `y` (array of numbers, same length as `x`): dependent-variable data.
- `initial_guess` (array of numbers, same length as `parameter_names`):
  starting point for the fit — nonlinear least squares has no
  parameter-free default the way a bracketed root-finder does; a
  starting point is always required.

# Optional inputs

- `bounds` (array of `[lo, hi]` pairs, same length/order as
  `parameter_names`; either side may be `null` for unbounded).
- `method` (string, one of `lm`/`trf`/`dogbox`): if omitted, selected by
  the rule in "Official methodology" below.
- `max_iterations` (integer, > 0): forwarded as SciPy's `maxfev`
  (method `lm`) or `max_nfev` (`trf`/`dogbox`) — this skill picks the
  right keyword for the resolved method automatically.

There is no `tolerance` input in this MVP: SciPy's per-method
convergence tolerances (`ftol`/`xtol`/`gtol`) are not exposed
individually — see "Known limitations".

# Units and dimensions

Dimensionless by design, matching every other `mathematics.*` MVP
skill.

# Official methodology

Method selection is explicit and documented, never inferred silently
(plan section 4.4): **no `bounds` selects `lm`** (Levenberg-Marquardt,
SciPy's classic unconstrained least-squares solver — it does not
support bounds at all); **`bounds` selects `trf`** (Trust Region
Reflective). `dogbox` is available as an explicit alternative to `trf`
for bounded problems; never auto-selected. Combining `bounds` with
`method: lm` is rejected (`INVALID`), not silently switched to `trf`.

# Mathematical formulation

- **Levenberg-Marquardt** (`lm`): interpolates between Gauss-Newton and
  gradient descent via a damping parameter, adjusted each iteration —
  the standard unconstrained nonlinear least-squares algorithm
  (Levenberg 1944, Marquardt 1963).
- **Trust Region Reflective** (`trf`): a trust-region method with a
  reflective transformation handling box bounds directly (Branch,
  Coleman & Li, 1999).
- **`dogbox`**: another bounded trust-region variant, using a
  dogleg-style step; occasionally more robust than `trf` for
  small-residual problems.

# Assumptions

- `model`/data are real-valued.
- Ordinary (unweighted) least squares: every data point contributes
  equally to the objective. A caller who needs to down-weight noisy
  points must pre-scale the residual manually (e.g. by pre-transforming
  `y`) — no `sigma` input in this MVP.
- **The result is a local minimum of the least-squares objective, not
  necessarily the global one** — same caveat as
  `mathematics.optimize_scalar`/`mathematics.optimize_constrained`,
  now for the residual-sum-of-squares surface: a nonlinear model (e.g.
  a sinusoid, where the frequency parameter creates many periodic local
  minima) can converge to a visibly wrong fit from a poor
  `initial_guess`. See "Worked examples" for a concrete case where a
  bad guess on a frequency parameter locks onto the wrong period
  entirely.
- At least as many data points as parameters (`len(x) >= len(parameter_names)`)
  — otherwise the fit is underdetermined; checked before execution
  (`INVALID`, not a confusing SciPy failure inside the sandbox).

# Conventions

`x` is the fixed name for the independent variable (never included in
`parameter_names`); every other symbol in `model` must be declared in
`parameter_names`.

# Applicability limits

- No per-point weighting (`sigma`)/covariance-of-observations input.
- No `tolerance` override (SciPy per-method defaults are used).
- `max_iterations` bounds the search; exhausting it returns
  `diagnostics.converged = false` (see "Failure conditions"), not an
  error.

# Validation rules

Implemented in `validation.py` (`CurveFitValidator`, layer
`mathematical`), run before execution:

- `parameter_names` must have no duplicates and must not contain `"x"`.
- `x`/`y` must have equal length; `len(x) >= len(parameter_names)`.
- `initial_guess` must have the same length as `parameter_names`.
- If `bounds` is given: same length as `parameter_names`; each pair
  with both sides non-null must have `lo < hi`.
- `model` must parse under the restricted-AST grammar against exactly
  `x` plus the declared `parameter_names` — an unknown name is an
  `ERROR`-severity outcome, not a crash.

The JSON Schema layer (`input.schema.json`) separately enforces types,
array shapes, `max_iterations > 0`, `constraints[].type`-style enums,
and rejects unknown top-level properties.

# Numerical diagnostics

`diagnostics` always contains: `method`, `converged` (bool —
**required**, per ADR 0013, since this skill's method is always
iterative), `message`, `n_iterations` (mirrors
`n_function_evaluations` — SciPy's `curve_fit` reports no separate
iteration count, unlike `minimize`/`minimize_scalar`'s `OptimizeResult.nit`;
not fabricated), `n_function_evaluations`, `residuals` (the vector
`yᵢ - f(xᵢ; p*)` at the fitted solution), `covariance` (the parameter
covariance matrix SciPy returns — reported as-is, including `inf`/`nan`
entries when the fit is poorly determined; never hidden).
`optimality`/`constraint_violation`/`feasible` are always `None` here —
they belong to `mathematics.optimize_constrained`'s diagnostics, not
curve fitting.

On non-convergence (`diagnostics.converged = false`): `params`,
`residuals`, and `covariance` reflect the **initial guess**
`initial_guess`, not a solver iterate — SciPy's `curve_fit` raises a
bare `RuntimeError` on failure with no partial-progress state to fall
back on; this skill does not fabricate one.

# Alternative methods

- `dogbox` over `trf` for small-residual bounded problems where `trf`
  converges slowly.
- `mathematics.optimize_constrained` is the right tool for minimizing
  an arbitrary scalar objective (not specifically a sum-of-squared
  residuals against data) with general nonlinear constraints.

# Failure conditions

- `model` fails to parse or references an unknown name → `INVALID`.
- `x`/`y` length mismatch, insufficient data points for the parameter
  count, `initial_guess`/`bounds` length mismatch, or a degenerate
  bound pair → `INVALID`.
- Duplicate or reserved (`"x"`) names in `parameter_names` → `INVALID`.
- `bounds` combined with `method: lm` → `INVALID`.
- SciPy's least-squares solver fails to converge (raises internally) →
  `diagnostics.converged = false`, status `INCONCLUSIVE` (ADR 0007) —
  not an error.

# Worked examples

**Exact linear recovery**: `y = 2x + 1`, noiseless →
`{"params": [2.0, 1.0], "method": "lm", ...}` (the true parameters are
known by construction, since the data was generated from them — the
independent oracle for this golden case).

**Exact nonlinear recovery**: `y = 3·sin(1.7x) + 0.5`, noiseless, from
`initial_guess = [2.5, 1.5, 0]` → recovers `[3.0, 1.7, 0.5]` essentially
exactly.

**Initial-guess sensitivity** (same sinusoid data, different
`initial_guess`): starting from `[2.5, 0.3, 0]` (a frequency guess far
from the true `b=1.7`) converges to a *different*, visibly wrong local
optimum instead — `diagnostics.converged` is still `true` (SciPy
reports success — it found *a* local minimum of the least-squares
surface, just not the one matching the true generating parameters).
This is not a bug: it demonstrates explicitly (skill.md "Assumptions")
that nonlinear least squares is a local method, and a poor
`initial_guess` on a periodic parameter is a classic failure mode this
skill does not protect against.

See `examples/` for the full request/response pairs used in
`tests/test_golden.py`.

# References

- Levenberg, K. (1944). *A Method for the Solution of Certain
  Non-Linear Problems in Least Squares*. Quarterly of Applied
  Mathematics.
- Marquardt, D. W. (1963). *An Algorithm for Least-Squares Estimation
  of Nonlinear Parameters*. SIAM Journal on Applied Mathematics.
- Branch, M. A., Coleman, T. F., Li, Y. (1999). *A Subspace, Interior,
  and Conjugate Gradient Method for Large-Scale Bound-Constrained
  Minimization Problems*. SIAM Journal on Scientific Computing.
- SciPy documentation: `scipy.optimize.curve_fit`.

# Known limitations

- No global-optimization guarantee — see "Assumptions".
- No per-point weighting / observation covariance (`sigma`).
- No `tolerance` override.
- On non-convergence, diagnostics reflect `initial_guess`, not a solver
  iterate (SciPy exposes none on `RuntimeError`).

# Changelog

- 0.1.0: initial version. Sprint 05, Fase B/C; third consumer of
  `oec.kernel.optimization`'s shared `OptimizationDiagnostics` contract,
  first to populate `residuals`/`covariance`.
