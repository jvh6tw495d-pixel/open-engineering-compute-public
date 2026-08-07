---
id: mathematics.optimize_scalar
version: 0.1.0
status: experimental
domain: mathematics
title: Optimize Scalar
---

# Purpose

Find a local minimizer of a scalar, user-supplied function `f(x)`, using
a numerically appropriate method chosen by explicit, documented rules —
never a silent LLM guess. Sprint 05's template skill: the first of the
`oec.kernel.optimization` family, establishing the multi-field
diagnostics contract (`OptimizationDiagnostics`) that
`math.optimize_constrained` and `math.curve_fit` also report through.

# Problem definition

Given `f: ℝ → ℝ` expressed as a mathematical expression string, find
`x*` that minimizes `f` — either within a caller-given interval
`[lo, hi]`, or unconstrained (SciPy's own internal bracketing decides
where to look). To maximize `f`, minimize `-f` — this skill has no
separate maximize mode, by design.

# Supported problem classes

- **Bounded minimization**: a minimum known to lie in `[lo, hi]`, found
  via Brent's method restricted to the interval (SciPy's `bounded`).
- **Unbounded minimization**: no interval given; SciPy searches from an
  internally constructed bracket via `brent` (default) or `golden`.

# Required inputs

- `expression` (string): `f(x)` as a mathematical expression in the
  single variable `x`. Parsed by the same restricted AST evaluator used
  by `mathematics.solve_root` (plan section 4.7) — arithmetic,
  `sin/cos/tan/asin/acos/atan/sinh/cosh/tanh/exp/log/log10/log2/sqrt/abs`,
  the constants `pi`/`e`, and `x` itself. No other names, attribute
  access, or calls are accepted.

# Optional inputs

- `bounds` (array of 2 numbers `[lo, hi]`, `lo < hi`): required for
  `method: bounded`, rejected for `brent`/`golden`.
- `method` (string, one of `bounded`/`brent`/`golden`): if omitted,
  selected by the explicit rule in "Official methodology" below.
- `tolerance` (number, > 0): convergence tolerance passed to SciPy as
  `tol`. Defaults to SciPy's own per-method default.
- `max_iterations` (integer, > 0): iteration cap. Default is SciPy's own
  (`bounded`: 500; `brent`/`golden`: 500).

# Units and dimensions

Dimensionless by design, matching `mathematics.solve_root`. A caller
minimizing a physically-dimensioned objective is responsible for
non-dimensionalizing it before calling this skill.

# Official methodology

Method selection is explicit and documented, never inferred silently
(plan section 4.4):

| Caller gives | Caller omits `method` | Method used |
|---|---|---|
| `bounds` | — | `bounded` (Brent restricted to the interval — the only one of the three methods that accepts `bounds` at all) |
| nothing (no `bounds`) | — | `brent` (unconstrained Brent; more robust than `golden`, the more conservative fallback) |
| any | `method` given explicitly | the given method, validated against what was provided (`bounded` without `bounds` is rejected, not silently run unconstrained; `bounds` with `brent`/`golden` is rejected, not silently dropped) |

`golden` (golden-section search) is available as an explicit alternative
to `brent` for unconstrained minimization — simpler, unconditionally
convergent for unimodal functions, but linear rather than superlinear
convergence. Never auto-selected.

# Mathematical formulation

- **Brent's method** (`bounded`/`brent`): combines golden-section search
  with successive parabolic interpolation; superlinear convergence near
  the minimum while retaining golden-section's robustness.
- **Golden-section search** (`golden`): repeatedly narrows a bracketing
  triple using the golden ratio, without assuming smoothness beyond
  unimodality. Linear convergence, no derivative information used.

# Assumptions

- `f` is real-valued and continuous on the relevant interval/neighborhood.
- **The result is a local minimum, not necessarily the global one.**
  Brent and golden-section both operate on a single bracket (the given
  `bounds`, or one SciPy constructs internally when unbounded); a
  function with multiple minima can have several distinct local minima,
  and this skill returns whichever one the chosen bracket contains — see
  "Worked examples" for a concrete multi-minima case. Finding a *global*
  minimum over multiple basins is out of scope; a caller who suspects
  multiple minima should call this skill once per candidate interval and
  compare `fun` across calls.
- The objective is assumed unimodal within the search interval for
  golden-section's convergence guarantee to hold; Brent tolerates mild
  deviation from unimodality but is not guaranteed to find the global
  minimum either.

# Conventions

`x` is the only accepted independent-variable name in `expression`,
matching `mathematics.solve_root`.

# Applicability limits

- Only real, scalar (single-variable), unconstrained-or-box-bounded
  minimization. No multi-variable objectives, no general nonlinear
  constraints — see `math.optimize_constrained` (Sprint 05, Fase B) for
  that.
- `max_iterations` bounds the search; exhausting it returns
  `diagnostics.converged = false` (see "Failure conditions"), not an
  error — the caller decides whether to retry with a larger budget.
- No maximize mode: minimize `-f(x)` and negate `fun` to interpret the
  result as a maximization.

# Validation rules

Implemented in `validation.py` (`OptimizeScalarValidator`, layer
`mathematical`), run before execution:

- `method: bounded` requires `bounds`; `bounds` is rejected with any
  other method (schema-level `oneOf`-style cross-field presence,
  awkward to express purely in JSON Schema, so checked here instead —
  mirrors `SolveRootValidator`'s `bracket`/`initial_guess` rule).
- If `bounds` is given: `lo < hi` (a degenerate or inverted interval is
  `INVALID`, not passed to SciPy to raise `ValueError` inside the
  sandbox).
- `expression` must parse under the restricted-AST grammar — a parse
  failure is an `ERROR`-severity outcome, not a crash.

The JSON Schema layer (`input.schema.json`) separately enforces types,
`tolerance > 0`, `max_iterations > 0`, `bounds` array shape, and rejects
unknown properties.

# Numerical diagnostics

`diagnostics` always contains: `method` (which SciPy method actually
ran), `converged` (bool — **required**, per ADR 0013, since this
skill's method is always iterative), `message` (SciPy's own
termination message), `n_iterations`, `n_function_evaluations`. The
shared `OptimizationDiagnostics` model also defines `optimality`,
`constraint_violation`, `feasible`, `residuals`, `covariance` for the
sibling optimization skills — none apply to unconstrained/box-bounded
scalar minimization, so this skill never sets them (they stay `None`,
not fabricated).

# Alternative methods

- `golden` over `brent`/`bounded` when the objective is known to be
  non-smooth (Brent's parabolic interpolation step assumes local
  smoothness; golden-section does not).
- A future `math.optimize_constrained` skill (Sprint 05, Fase B) is the
  right place for multi-variable objectives and general nonlinear
  constraints — out of scope here by design.

# Failure conditions

- `expression` fails to parse or references a disallowed name/call →
  `INVALID` (validation layer, execution never runs).
- `method: bounded` without `bounds`, or `bounds` with a non-`bounded`
  method → `INVALID`.
- `bounds` with `lo >= hi` → `INVALID`.
- Iteration budget exhausted without convergence →
  `diagnostics.converged = false`, status `INCONCLUSIVE` (ADR 0007) —
  not an error; `result.x`/`result.fun` still name the last iterate
  SciPy reached, but it is not to be trusted as a minimizer.

# Worked examples

`{"expression": "(x - 3)**2", "bounds": [0, 10], "method": "bounded"}` →
`{"x": 3.0, "fun": 0.0, "method": "bounded", ...}` (the unconstrained
global minimum lies inside the bounds, so it's found exactly).

`{"expression": "(x - 2)**2"}` → `{"x": 1.9999999999999998, "fun": ~5e-32, "method": "brent", ...}`
(method auto-selected as `brent` since no `bounds` were given).

**Multi-minima case** — `f(x) = x**4 - x**2` has two symmetric global
minima at `x = ±1/√2 ≈ ±0.7071`, `fun = -0.25` (found via
`f'(x) = 4x³ - 2x = 0 ⟹ x ∈ {0, ±1/√2}`, `f''(±1/√2) = 4 > 0` confirms
a minimum; `f''(0) = -2 < 0` confirms `x=0` is a local *maximum*, not a
minimum). Restricting `bounds` to `[-2, 0]` finds the left one
(`x ≈ -0.7071`); restricting to `[0, 2]` finds the right one
(`x ≈ 0.7071`) — same `fun`, different `x`, purely a function of which
bracket was searched. See `examples/` and
`tests/test_golden.py::test_double_well_*` for the full cases.

See `examples/` for the full request/response pairs used in
`tests/test_golden.py`.

# References

- Brent, R. P. (1973). *Algorithms for Minimization Without
  Derivatives*. Prentice-Hall, Chapter 5.
- Press, W. H. et al. (2007). *Numerical Recipes*, 3rd ed., Sections
  10.2 (golden-section search) and 10.3 (Brent's method).
- SciPy documentation: `scipy.optimize.minimize_scalar`.

# Known limitations

- No global-optimization guarantee — see "Assumptions" above.
- No maximize mode (minimize the negated expression instead).
- No multi-variable support — see `math.optimize_constrained`.

# Changelog

- 0.1.0: initial version. Sprint 05 template skill; establishes
  `oec.kernel.optimization`'s diagnostics contract.
