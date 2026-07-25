---
id: mathematics.interpolate
version: 0.1.0
status: experimental
domain: mathematics
title: Interpolate
---

# Purpose

Build a 1-D interpolant from discrete samples `(x_i, y_i)` and evaluate
it at caller-chosen query points. Method is **always** chosen
explicitly by the caller — never auto-selected — because the three
supported methods answer different engineering questions (robustness
vs. smoothness vs. shape preservation).

# Problem definition

Given samples `(x_i, y_i)` with strictly increasing abscissae, produce
`ŷ(q)` for each query abscissa `q` in `query_points`, where `ŷ` is the
interpolant implied by the chosen `method`.

# Supported problem classes

- **Piecewise linear interpolation** (`linear`): connects samples with
  straight segments. Robust, no overshoot between samples.
- **Cubic spline interpolation** (`cubic_spline`): C² piecewise cubic
  with not-a-knot end conditions. Smooth, but may overshoot.
- **PCHIP / monotone cubic** (`pchip`): piecewise cubic Hermite that
  preserves local monotonicity of the data (Fritsch–Carlson).

# Required inputs

- `x` (array of numbers, length ≥ 2): strictly increasing sample
  abscissae.
- `y` (array of numbers, same length as `x`): sample ordinates.
- `query_points` (array of numbers, length ≥ 1): abscissae at which to
  evaluate the interpolant.
- `method` (string, one of `linear` / `cubic_spline` / `pchip`):
  **mandatory, no default**. See "Official methodology" for why there
  is no auto-selection here (contrast with `mathematics.solve_root`).

# Optional inputs

None. All four fields above are required; there are no tolerance or
iteration knobs because interpolation is a direct construction, not an
iterative solver.

# Units and dimensions

Dimensionless by design. `math.interpolate` operates on abstract
numeric samples; it does not accept `QuantityValue`-shaped inputs. A
caller interpolating dimensioned quantities is responsible for
non-dimensionalizing (or keeping units consistent) before calling this
skill — units enter the picture with the domain skills (Sprint 08+).

# Official methodology

**There is no auto-selection of `method`.** Unlike `mathematics.solve_root`
— where bracket-vs-guess gives a natural default (`brentq` vs. `secant`)
— the three interpolants here are philosophically different and none is
"more correct" by default:

| Method | Prefer when… | Trade-off |
|---|---|---|
| `linear` | robustness and simplicity matter; no overshoot acceptable | only C⁰; larger interpolation error on smooth curves |
| `cubic_spline` | smoothness (C²) matters and samples are dense enough | can overshoot between samples; needs ≥ 4 points |
| `pchip` | data are (locally) monotone and shape must be preserved | less smooth than a cubic spline (C¹ only) |

Requiring the caller to name the method makes that engineering choice
auditable in the provenance record (plan section 4.4: method selection
is explicit and documented, never a silent LLM guess).

# Mathematical formulation

- **Linear** (`numpy.interp`): on each interval `[x_i, x_{i+1}]`,
  `ŷ(q) = y_i + (y_{i+1} - y_i) · (q - x_i) / (x_{i+1} - x_i)`.
- **Cubic spline** (`scipy.interpolate.CubicSpline`, `bc_type="not-a-knot"`):
  piecewise cubics with continuous first and second derivatives; end
  cubics match the next interior cubic's third derivative at the first
  interior knot (not-a-knot).
- **PCHIP** (`scipy.interpolate.PchipInterpolator`): piecewise cubics
  with Hermite slopes chosen so that local monotonicity of the data is
  preserved (Fritsch–Carlson algorithm).

# Assumptions

- `x` is strictly increasing (no duplicate abscissae, no inversions) —
  checked before execution.
- Samples are exact (no measurement-error model); noise handling is out
  of scope (use a dedicated smoothing/regression skill later).
- Evaluation outside `[min(x), max(x)]` is *extrapolation* of the same
  interpolant (see "Applicability limits"), not a different algorithm.

# Conventions

- Output `values[i]` corresponds to `query_points[i]` in the same order.
- `linear` uses `numpy.interp`'s edge rule: query points outside
  `[min(x), max(x)]` clamp to the nearest endpoint value. `cubic_spline`
  and `pchip` extrapolate the end polynomial pieces (SciPy default
  `extrapolate=True` for both constructors as used here).

# Applicability limits

- 1-D only. No multi-variate / scattered-data interpolation.
- `cubic_spline` requires `len(x) >= 4` (not-a-knot needs enough interior
  knots); fewer points → `INVALID` with a clear message (use `linear`
  or `pchip`).
- Query points outside `[min(x), max(x)]` are **not** an error: the
  interpolant is still evaluated, but validation emits a
  `Severity.WARNING` because extrapolation is less reliable than
  interpolation inside the sample hull. Status becomes
  `CONVERGED_WITH_WARNINGS` (ADR 0007) rather than `VERIFIED`.
- No denseness / sampling-quality check: a badly sampled curve yields a
  faithful interpolant of the samples, not of the underlying function.

# Validation rules

Implemented in `validation.py` (`InterpolateValidator`, layer
`mathematical`), run before execution:

- `len(x) == len(y)`.
- `x` strictly increasing.
- `method: cubic_spline` requires `len(x) >= 4`.
- Any `query_point` outside `[min(x), max(x)]` → `WARNING` (not
  `ERROR`).

The JSON Schema layer separately enforces types, required fields,
`method` enum, and minimum array lengths, and rejects unknown
properties.

# Numerical diagnostics

`diagnostics` always contains: `method` (which interpolant ran),
`n_samples` (`len(x)`), `n_query` (`len(query_points)`).

Because this skill's method is **not iterative**
(`method.iterative: false` in `skill.yaml`), `diagnostics` does **not**
include `converged` — there is no iteration that can fail to converge
(ADR 0013: only iterative methods must report it; exact/closed-form
methods keep `converged is None` for `compute_status`).

# Alternative methods

- For noisy samples, prefer a smoothing spline or regression skill
  (future) over forcing an interpolant through every point.
- For shape-preserving needs on non-monotone data with known extrema,
  consider a future tension-spline / Akima option — out of scope here.
- Multi-dimensional interpolation belongs in a separate skill.

# Failure conditions

- Missing required field / wrong type / unknown property → `INVALID`
  (schema layer).
- `len(x) != len(y)` → `INVALID`.
- `x` not strictly increasing → `INVALID`.
- `cubic_spline` with fewer than 4 samples → `INVALID`.
- Extrapolation (query outside sample range) → execution still runs;
  status `CONVERGED_WITH_WARNINGS` via the validation `WARNING`.

# Worked examples

Linear samples of `y = 2x` at `x = [0, 1, 2, 3]`, query midpoints →
exact values `[1.0, 3.0, 5.0]` (closed-form linear).

Cubic spline of `y = x**3` at five knots, query half-integers → exact
cubic values (a cubic spline recovers a cubic polynomial under
not-a-knot).

See `examples/` for the full request/response pairs used in
`tests/test_golden.py`.

# References

- Burden, R. L., Faires, J. D. (2011). *Numerical Analysis*, 9th ed.,
  Chapter 3.
- Fritsch, F. N., Carlson, R. E. (1980). Monotone Piecewise Cubic
  Interpolation. *SIAM J. Numer. Anal.* 17(2).
- SciPy / NumPy: `numpy.interp`, `CubicSpline`, `PchipInterpolator`.

# Known limitations

- No multi-dimensional or unstructured-mesh interpolation.
- No uncertainty / noise model on the samples.
- Extrapolation behaviour differs between methods (`linear` clamps;
  spline/PCHIP extend end pieces) — callers doing out-of-range queries
  should treat results with the emitted WARNING in mind.

# Changelog

- 0.1.0: initial version (Sprint 04). Linear, cubic spline, and PCHIP
  interpolation; mandatory `method`; extrapolation as WARNING.
