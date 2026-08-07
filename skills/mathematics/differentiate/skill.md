---
id: mathematics.differentiate
version: 0.1.0
status: experimental
domain: mathematics
title: Numerical Differentiation (Finite Difference)
---

# Purpose

Estimate `f'(x)` for a scalar, user-supplied function `f(x)`, at a single
point, via finite differences. The first real consumer of the new
`kernel/computational` differentiation module (ADR 0022) — no
differentiation capability existed anywhere in OEC before this skill.

# Problem definition

Given `f: ℝ → ℝ` expressed as a mathematical expression string and a point
`x`, estimate `f'(x)` using the central, forward, or backward
finite-difference formula.

# Required inputs

- `expression` (string): `f(x)` as a mathematical expression in the single
  variable `x`, same restricted-AST grammar as `mathematics.solve_root`
  (arithmetic, `sin/cos/tan/asin/acos/atan/sinh/cosh/tanh/exp/log/log10/
  log2/sqrt/abs`, constants `pi`/`e`, and `x` itself).
- `at` (number): the point to differentiate at.

# Optional inputs

- `method` (string, one of `central`/`forward`/`backward`): defaults to
  `central` — second-order accurate, needs `f` evaluable on both sides of
  `at`.
- `step` (number, > 0): the finite-difference step `h`. If omitted, an
  adaptive step balancing truncation error against floating-point
  roundoff is used (see "Official methodology").

# Official methodology

Method id: `finite_difference`. Not iterative — a closed-form estimate at
a fixed step, not an adaptive solver; `diagnostics.converged` is always
`null` (ADR 0013), matching `mathematics.interpolate`'s convention for
exact, non-iterative results.

Default step sizes: `h = max(|x|, 1) · ε^(1/3)` for `central`
(minimizes the sum of O(h²) truncation error and O(ε/h) roundoff error);
`h = max(|x|, 1) · ε^(1/2)` for `forward`/`backward` (O(h) truncation
error). `ε` is IEEE 754 double machine epsilon.

`scipy.misc.derivative` (the function this would otherwise wrap) was
removed from modern SciPy, and `scipy.optimize.approx_fprime` only
supports forward differences with no step control — this skill's kernel
module implements the three formulas directly instead.

# Assumptions

- `f` is real-valued and differentiable in a neighborhood of `at`.
- Scalar-to-scalar only: no gradient/Jacobian for vector-valued or
  multivariate functions in this version.

# Applicability limits

- One point at a time — no vectorized evaluation over an array of points.
- No symbolic or automatic differentiation; purely numerical estimation,
  subject to finite-difference truncation and roundoff error.

# Validation rules

Implemented in `validation.py` (`DifferentiateValidator`, layer
`mathematical`): `expression` must parse under the restricted-AST grammar;
`step`, if given, must be a positive, finite number.

# Numerical diagnostics

`diagnostics` contains: `method` (`central`/`forward`/`backward`) and
`step` (the finite-difference step actually used, whether given or
defaulted).

# Worked examples

`{"expression": "x**2", "at": 3.0}` → `{"value": 6.0}` (central difference;
exact up to floating-point roundoff since `x**2`'s third derivative is
zero, so truncation error vanishes identically).

See `examples/` for the full request/response pairs used in
`tests/test_golden.py`.

# References

- Burden, R. L., Faires, J. D. (2011). *Numerical Analysis*, 9th ed.,
  Chapter 4.
- `docs/architecture/adr/0022-computational-kernel-unification.md`.

# Known limitations

- Scalar-to-scalar only (no gradient/Jacobian).
- No adaptive step refinement or Richardson extrapolation.

# Changelog

- 0.1.0: initial version, part of the v2.5 computational kernel
  unification (ADR 0022).
