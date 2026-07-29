---
id: timeseries.levinson_durbin
version: 0.1.0
status: experimental
domain: timeseries
title: Levinson-Durbin Toeplitz Solve
---

# Purpose

Solve the symmetric Toeplitz (Yule-Walker) system implied by an
autocorrelation/autocovariance sequence `[r0, r1, ..., rp]` via the
Levinson-Durbin recursion, in `O(p^2)` time without forming or inverting
the full `(p+1)x(p+1)` Toeplitz matrix. This is the shared engine behind
`timeseries.pacf` and `timeseries.ar_yule_walker`; this skill exposes it
directly for callers who already have an autocorrelation sequence in
hand (e.g. from a source outside OEC) and only need the Toeplitz solve.

# Official methodology

Method id: `levinson_durbin`. Given `r0 > 0` and `r1..rp`, the recursion
builds, for each order `k = 1..p`:

- the reflection coefficient `phi_k = (r_k - sum_{j=1}^{k-1} a_{k-1,j}
  r_{k-j}) / E_{k-1}`;
- the updated AR coefficients `a_{k,j} = a_{k-1,j} - phi_k a_{k-1,k-j}`
  for `j=1..k-1`, and `a_{k,k} = phi_k`;
- the updated prediction-error variance `E_k = E_{k-1} (1 - phi_k^2)`.

**A real (positive-semidefinite) autocorrelation sequence guarantees
`|phi_k| < 1` at every step.** If the input sequence violates this — it
was estimated with the "unbiased" estimator, or handed in from an
external, possibly non-PSD source — the recursion stops at the last
valid order rather than continuing into a numerically meaningless
region. `is_positive_definite=false` and `order_reached < order_requested`
report this honestly; `ar_coefficients`/`reflection_coefficients` cover
only the orders actually reached.

`method.iterative` is `false`: a fixed, input-size-determined number of
steps, not an iterative solver seeking convergence (ADR 0013 amendment).
`converged` is `None`.

# Applicability limits

- `autocorrelation` must be a 1-D array of at least 2 finite numbers.
- `autocorrelation[0]` (the process variance) must be strictly positive.

# Failure conditions

- `autocorrelation[0] <= 0`: rejected by validation before execution
  (the recursion cannot start).
- Non-finite entries: rejected by validation before execution.
- A non-positive-definite sequence (e.g. `|r1/r0| >= 1`) does not raise —
  it stops the recursion early and reports `is_positive_definite=false`;
  see "Official methodology" above. This is a reported outcome, not an
  exception, because the input was well-formed even though it wasn't a
  valid autocorrelation sequence.

# Alternative methods

- `timeseries.autocorrelation` + this skill, chained by hand, is
  equivalent to `timeseries.pacf`/`timeseries.ar_yule_walker` — those two
  skills exist so callers starting from a raw series don't have to wire
  the two calls together themselves.

# Known limitations

- Real-valued sequences only; no complex/vector (multichannel) Toeplitz
  systems.

# Changelog

- 0.1.0: initial (v2.5.1 — AR/autocorrelation package).
