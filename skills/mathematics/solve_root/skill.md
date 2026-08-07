---
id: mathematics.solve_root
version: 0.1.0
status: experimental
domain: mathematics
title: Solve Root
---

# Purpose

Find a real root of a scalar, user-supplied function `f(x) = 0`, using a
numerically appropriate method chosen by explicit, documented rules —
never a silent LLM guess. This is OEC's first real engineering skill and
the template every later skill's package layout, diagnostics contract,
and golden-case format is copied from.

# Problem definition

Given `f: ℝ → ℝ` expressed as a mathematical expression string, find
`x*` such that `f(x*) ≈ 0`, within a caller-specified tolerance.

# Supported problem classes

- **Bracketed root finding**: a real root known to lie in `[a, b]`,
  where `f(a)` and `f(b)` have opposite signs.
- **Root finding from an initial guess**: a starting point `x0` near an
  expected root, no bracket known.

# Required inputs

- `expression` (string): `f(x)` as a mathematical expression in the
  single variable `x`. Parsed by a restricted AST evaluator (plan
  section 4.7) — arithmetic, `sin/cos/tan/asin/acos/atan/sinh/cosh/tanh/
  exp/log/log10/log2/sqrt/abs`, the constants `pi`/`e`, and `x` itself.
  No other names, attribute access, or calls are accepted.

Exactly one of the following must also be given:

- `bracket` (array of 2 numbers `[a, b]`): required for `method: brentq`
  or `method: bisect`, or when `method` is omitted and a bracket is the
  only locator given.
- `initial_guess` (number): required for `method: secant` or
  `method: newton`, or when `method` is omitted and only a guess is given.

# Optional inputs

- `method` (string, one of `brentq`/`bisect`/`secant`/`newton`): if
  omitted, selected by the explicit rule in "Official methodology"
  below.
- `derivative` (string): `f'(x)`, same restricted-expression grammar as
  `expression`. Required if and only if `method: newton`.
- `tolerance` (number, > 0): convergence tolerance passed to the
  underlying SciPy solver. Defaults to SciPy's own default per method
  (`brentq`/`bisect`: `xtol=2e-12`; `secant`/`newton`: `tol=1.48e-08`).
- `max_iterations` (integer, > 0): iteration cap. Default `100` for
  bracketed methods, `50` for guess-based methods.

# Units and dimensions

Dimensionless by design. `math.solve_root` operates on an abstract
scalar function; it does not accept `QuantityValue`-shaped inputs. A
caller solving a physically-dimensioned equation is responsible for
non-dimensionalizing it before calling this skill — that is out of
scope here (units enter the picture with the electrical skills,
Sprint 08).

# Official methodology

Method selection is explicit and documented, never inferred silently
(plan section 4.4):

| Caller gives | Caller omits `method` | Method used |
|---|---|---|
| `bracket` | — | `brentq` (Brent's method: superlinear convergence, as robust as bisection) |
| `initial_guess` only | — | `secant` (no derivative required) |
| `initial_guess` + `derivative` | — | still `secant` unless `method: newton` is given explicitly — providing a derivative does not silently switch methods |
| any | `method` given explicitly | the given method, validated against what was provided (e.g. `method: newton` without `derivative` is rejected, not silently downgraded to `secant`) |

`bisect` is available as an explicit alternative to `brentq` for a
bracketed root — strictly slower (linear convergence) but simpler and
occasionally preferred for its guaranteed, easily-reasoned-about
behavior. It is never auto-selected.

# Mathematical formulation

- **Brent's method** (`brentq`): combines bisection, secant, and inverse
  quadratic interpolation; converges superlinearly while retaining
  bisection's guarantee (a bracket with a sign change always converges).
- **Bisection** (`bisect`): repeatedly halves `[a, b]`, keeping the half
  containing the sign change. Linear convergence, unconditionally
  reliable given a valid bracket.
- **Secant method**: `x_{n+1} = x_n - f(x_n) · (x_n - x_{n-1}) / (f(x_n) - f(x_{n-1}))`,
  approximating the derivative from two prior points. Superlinear
  convergence (order ≈ 1.618), no derivative required.
- **Newton's method**: `x_{n+1} = x_n - f(x_n) / f'(x_n)`. Quadratic
  convergence near a simple root, requires an analytic derivative.

# Assumptions

- `f` is real-valued and continuous on the relevant interval/neighborhood.
- For bracketed methods: `f(a)` and `f(b)` have strictly opposite signs
  (checked before execution — see "Validation rules").
- For Newton's method: `f'` is the true derivative of `f` (not checked
  numerically; an incorrect derivative produces a wrong or
  non-converging result, surfaced via `diagnostics.converged`).
- The root sought is a **simple** root (multiplicity 1). Multiple roots
  degrade convergence order for Newton/secant; this skill does not
  detect or special-case multiplicity.

# Conventions

`x` is the only accepted independent-variable name in `expression`/
`derivative`. There is no support for multi-variable expressions or for
naming the variable anything else.

# Applicability limits

- Only real, scalar (single-variable) root finding. No systems of
  equations, no complex roots.
- `max_iterations` bounds the search; a function with a root that
  requires more iterations than allotted returns
  `diagnostics.converged = false` (see "Failure conditions"), not an
  error — the caller decides whether to retry with a larger budget.
- Expressions are limited to the functions listed in "Required inputs";
  there is no way to reference external data, other skills' outputs, or
  arbitrary Python code from within `expression`.

# Validation rules

Implemented in `validation.py` (`SolveRootValidator`, layer
`mathematical`), run before execution:

- Exactly one of `bracket`/`initial_guess` must be present (schema-level
  `required`/`oneOf`-style presence is checked here, not purely in JSON
  Schema, since JSON Schema's cross-field conditionals are awkward for
  this shape).
- `expression` (and `derivative`, if given) must parse under the
  restricted-AST grammar — a parse failure is an `ERROR`-severity
  outcome, not a crash.
- If `bracket` is given: `f(a)` and `f(b)` must have opposite signs
  (`oec.validation.mathematical.require_bracket`) — checked *before*
  the sandboxed execution, so a bad bracket is `INVALID`, not a wasted
  subprocess spawn that eventually raises `NumericalDomainError`.
- `method: newton` requires `derivative`; `method` other than `newton`
  must not receive `derivative`.

The JSON Schema layer (`input.schema.json`) separately enforces types,
`tolerance > 0`, `max_iterations > 0`, and rejects unknown properties.

# Numerical diagnostics

`diagnostics` always contains: `method` (which solver actually ran),
`converged` (bool — **required**, per ADR 0013, since this skill's
method is always iterative), `iterations`, `function_calls`,
`residual` (`|f(root)|` at the returned root).

# Alternative methods

- Newton's method converges faster than secant when a correct
  derivative is available and the initial guess is close to the root —
  use `method: newton` with `derivative` explicitly when that applies.
- `bisect` over `brentq` when guaranteed, predictable step-halving
  behavior matters more than speed (e.g. reproducing a textbook
  bisection trace exactly).
- A future `math.solve_system` skill (not in this MVP) would be the
  right place for multi-variable/systems-of-equations root finding —
  out of scope here by design, not by oversight.

# Failure conditions

- `expression`/`derivative` fails to parse or references a disallowed
  name/call → `INVALID` (validation layer, execution never runs).
- `bracket` without a sign change → `INVALID`.
- `method: newton` without `derivative` (or vice versa: `derivative`
  given with a non-`newton` method) → `INVALID`.
- Neither `bracket` nor `initial_guess` given → `INVALID`.
- Iteration budget exhausted without convergence →
  `diagnostics.converged = false`, status `INCONCLUSIVE` (ADR 0007) —
  not an error; the result key still names the last iterate SciPy
  reached, but it is not to be trusted as a root.

# Worked examples

`{"expression": "x**2 - 2", "bracket": [0, 2]}` →
`{"root": 1.4142135623730951, "method": "brentq", "iterations": 8, "residual": ~1.2e-13}`
(√2, `method` auto-selected as `brentq` since only `bracket` was given).

`{"expression": "x**2 - 2", "initial_guess": 1.0}` →
`{"root": 1.414213562373095, "method": "secant", ...}`
(same root, `method` auto-selected as `secant`).

See `examples/` for the full request/response pairs used in
`tests/test_golden.py`.

# References

- Brent, R. P. (1973). *Algorithms for Minimization Without
  Derivatives*. Prentice-Hall, Chapter 4.
- Burden, R. L., Faires, J. D. (2011). *Numerical Analysis*, 9th ed.,
  Chapter 2 (bisection, Newton, secant methods and convergence orders).
- SciPy documentation: `scipy.optimize.brentq`, `bisect`, `newton`.

# Known limitations

- No complex-root support.
- No multiplicity detection for non-simple roots.
- `derivative` must be supplied by the caller as a literal expression —
  no symbolic or numerical differentiation of `expression` is performed
  by this skill.

# Changelog

- 0.1.0: initial version. Establishes the skill package template
  (layout, diagnostics contract, golden-case format) for Sprint 04.
