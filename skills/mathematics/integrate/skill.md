---
id: mathematics.integrate
version: 0.1.0
status: experimental
domain: mathematics
title: Integrate
---

# Purpose

Compute a definite integral either of a user-supplied scalar expression
`f(x)` over `[a, b]` (adaptive quadrature) or of tabulated samples
`(x_i, y_i)` (Newton–Cotes: Simpson or trapezoid). Mode is exclusive:
exactly one of the two input shapes is accepted.

# Problem definition

Estimate `I = ∫_a^b f(x) dx`, where `f` is given either as a restricted
expression string or as discrete samples.

# Supported problem classes

- **Function mode (adaptive quadrature)**: `expression` + `bounds`.
  Uses `scipy.integrate.quad` (QUADPACK).
- **Tabulated mode (Newton–Cotes)**: `x` + `y` sample arrays. Uses
  Simpson when applicable, trapezoid otherwise (or on request).

# Required inputs

Exactly one mode:

**Function mode**

- `expression` (string): `f(x)` in the same restricted AST grammar as
  `mathematics.solve_root` / `oec.kernel.numerics.expressions.compile_expression`
  — arithmetic, `sin/cos/tan/asin/acos/atan/sinh/cosh/tanh/exp/log/
  log10/log2/sqrt/abs`, constants `pi`/`e`, and `x`.
- `bounds` (array of 2 numbers `[a, b]`): integration limits; `a ≠ b`
  (orientation is preserved: `a > b` yields a signed integral).

**Tabulated mode**

- `x` (array of numbers, length ≥ 2): strictly increasing sample
  abscissae.
- `y` (array of numbers, same length as `x`): sample ordinates of `f`.

# Optional inputs

- `method` (string, `simpson` / `trapezoid`): **tabulated mode only**.
  If omitted, selected by the explicit rule in "Official methodology".
  Providing `method` in function mode is rejected (`INVALID`).
- `epsabs` (number, > 0): absolute tolerance for `quad` (function mode).
  Default `1.49e-08` (SciPy's default).
- `epsrel` (number, > 0): relative tolerance for `quad` (function mode).
  Default `1.49e-08`.

# Units and dimensions

Dimensionless by design. Same rationale as `mathematics.solve_root`:
callers non-dimensionalize before calling.

# Official methodology

## Mode selection (mandatory, exclusive)

| Caller gives | Mode |
|---|---|
| `expression` + `bounds` | function (adaptive `quad`) |
| `x` + `y` | tabulated (Simpson / trapezoid) |
| both or neither | `INVALID` |

## Tabulated method selection (explicit, documented — plan section 4.4)

| Caller gives | Rule |
|---|---|
| `method: trapezoid` | always trapezoid |
| `method: simpson` | Simpson if `len(x) ≥ 3`, else `INVALID` |
| `method` omitted, `len(x) ≥ 3` | **Simpson** (default) |
| `method` omitted, `len(x) == 2` | **trapezoid** (Simpson not applicable) |

Auto-selection is justified here (unlike `mathematics.interpolate`)
because the choice is forced by sample count: with only two points
Simpson is mathematically undefined, so falling back to trapezoid is
the unique applicable rule — the same spirit as `solve_root`'s
bracket-vs-guess default.

## Why `method.iterative: true` for the whole skill

`method.iterative` is a **static** declaration on `skill.yaml`; it
cannot change per call (ADR 0013). Function mode *is* genuinely
adaptive/iterative and needs the ADR 0013 protection (missing
`diagnostics["converged"]` must not silently become `VERIFIED`).
Declaring `iterative: true` for the skill is the conservative, safe
choice. The tabulated path is a fixed formula, but its
`implementation.py` always sets `diagnostics["converged"] = True`
(never omits the key) and documents that the rule is deterministically
exact given the samples — there is no iterative process that can fail.

# Mathematical formulation

- **Adaptive quadrature** (`quad`): adaptive Gauss–Kronrod / QUADPACK
  subdivision until the estimated absolute error is within
  `max(epsabs, epsrel · |I|)`.
- **Composite Simpson** (`scipy.integrate.simpson`): quadratic pieces on
  successive panels (handles even/odd panel counts per SciPy).
- **Composite trapezoid** (`scipy.integrate.trapezoid`): linear pieces
  between consecutive samples.

# Assumptions

- Function mode: `f` is integrable on the closed interval between the
  bounds (singularities at endpoints may still succeed via QUADPACK
  weights, but are not specially handled here).
- Tabulated mode: samples are exact ordinates of some `f`; the
  quadrature approximates `∫ f` under the usual piecewise-polynomial
  model. No noise / measurement-error model.

# Conventions

- Output `mode` is `"function"` or `"tabulated"` so callers and
  provenance can see which path ran without inspecting inputs.
- Technical fields (`abs_error`, chosen Newton–Cotes rule, …) live in
  `diagnostics`, not in `result` — same separation as
  `mathematics.solve_root`.

# Applicability limits

- Scalar, single-variable, definite integrals only. No multi-dimensional
  quadrature, no indefinite integrals, no ODE initial-value problems.
- Function mode is limited to the restricted expression grammar (no
  arbitrary Python, no external data).
- Tabulated mode needs `len(x) ≥ 2` and strictly increasing `x`.
- Very oscillatory or singular integrands may exhaust QUADPACK's
  internal subdivision budget and report `converged = false` (status
  `INCONCLUSIVE`) rather than raising.

# Validation rules

Implemented in `validation.py` (`IntegrateValidator`, layer
`mathematical`):

- Exactly one mode: (`expression` + `bounds`) XOR (`x` + `y`).
- Function: `expression` must parse; `bounds` length 2 with `a ≠ b`;
  `method` must not be present.
- Tabulated: `len(x) == len(y)`, `x` strictly increasing, `len(x) ≥ 2`;
  `method: simpson` requires `len(x) ≥ 3`.

JSON Schema separately enforces types, `epsabs`/`epsrel` positivity,
and rejects unknown properties.

# Numerical diagnostics

Always present: `mode`, `method` (the rule that actually ran),
`converged` (bool — **required**, ADR 0013).

Function mode additionally reports `abs_error` (QUADPACK estimate),
`epsabs`, `epsrel`, and `tolerance = max(epsabs, epsrel · |value|)`.
`converged` is `abs_error <= tolerance`.

Tabulated mode additionally reports `n_points`. `converged` is always
`True` (see "Official methodology").

# Alternative methods

- For higher-order tabulated rules (Boole, Romberg) or Gaussian
  quadrature with known weight functions, a future skill extension —
  out of scope for this MVP slice.
- Oscillatory integrands may benefit from specialized QUADPACK weight
  functions (`weight=` in `quad`); not exposed yet.

# Failure conditions

- Both modes or neither → `INVALID`.
- Expression parse failure / disallowed name → `INVALID`.
- Equal bounds / non-increasing `x` / length mismatch → `INVALID`.
- `method` with function-mode inputs, or `simpson` with < 3 points →
  `INVALID`.
- Adaptive quadrature whose error estimate exceeds tolerance →
  `diagnostics.converged = false`, status `INCONCLUSIVE` (ADR 0007);
  `result.value` still carries the last estimate.

# Worked examples

`{"expression": "sin(x)", "bounds": [0, pi]}` →
`{"value": 2.0, "mode": "function"}` (exact; `pi` is the allowed
constant in the expression grammar — here pass numeric `math.pi` or
use `pi` inside a larger expression; bounds are numeric).

`{"expression": "x**2", "bounds": [0, 1]}` →
`{"value": 0.333…, "mode": "function"}` (= 1/3).

Tabulated samples of `y = x**2` on a uniform grid with ≥ 3 points →
Simpson recovers 1/3 to machine precision (Simpson is exact for
quadratics).

See `examples/` for the full request/response pairs used in
`tests/test_golden.py`.

# References

- Burden & Faires, *Numerical Analysis*, Ch. 4.
- Piessens et al., *QUADPACK* (1983).
- SciPy: `quad`, `simpson`, `trapezoid`.
- mpmath: `quad` (golden-case oracle).

# Known limitations

- No multi-dimensional or contour integration.
- No automatic singularity detection beyond QUADPACK defaults.
- Tabulated path does not estimate quadrature error (only the function
  path has `abs_error`).

# Changelog

- 0.1.0: initial version (Sprint 04). Function (adaptive quad) and
  tabulated (Simpson/trapezoid) modes; skill-wide `iterative: true`.
