---
id: timeseries.ar_yule_walker
version: 0.1.0
status: experimental
domain: timeseries
title: AR Coefficient Estimation (Yule-Walker)
---

# Purpose

Fit an AR(`order`) model to `series` by the Yule-Walker method: estimate
the sample autocorrelation, then solve the resulting Toeplitz system for
the AR coefficients and the innovation (one-step prediction error)
variance.

# Official methodology

Method id: `yule_walker_levinson_durbin`. Internally:

1. `oec.kernel.timeseries.ar.autocorrelation(series, nlags=order,
   method="biased")` — always the biased estimator, never a caller
   choice, because it is the one guaranteed to yield a
   positive-semidefinite sequence (see `timeseries.autocorrelation`'s
   skill.md).
2. `oec.kernel.timeseries.ar.levinson_durbin(acf)` — solves the Toeplitz
   system for the final-order AR coefficients and the normalized
   prediction-error variance.
3. `innovation_variance = sample_variance * <normalized final-order
   prediction error>`, where `sample_variance` is the (biased) sample
   variance of the (optionally demeaned) series. This rescales the
   recursion's `r0=1`-normalized error back into the series' own units.

Because step 1 always uses the biased estimator, `is_positive_definite`
is mathematically guaranteed `true` and `order_reached` guaranteed to
equal `order` — both are still reported explicitly rather than assumed.

`method.iterative` is `false`. `converged` is `None` (ADR 0013
amendment: a fixed, input-size-determined recursion, not an iterative
solver seeking convergence).

# Applicability limits

- `series` must be a 1-D array of at least 2 finite numbers.
- `order` must satisfy `1 <= order < len(series)`.
- `series` must have nonzero variance.

# Failure conditions

- `order >= len(series)`: rejected by validation before execution.
- Zero-variance (constant) series: rejected by validation before execution.

# Alternative methods

- `timeseries.levinson_durbin` to solve the Toeplitz system directly from
  an already-known autocorrelation/autocovariance sequence, without going
  through a raw series.
- `timeseries.pacf` to inspect the partial autocorrelation and choose
  `order` yourself (the classic Box-Jenkins identification step) before
  calling this skill.

# Known limitations

- Only Yule-Walker estimation is implemented; conditional/exact maximum
  likelihood and Burg's method are not (Burg is a documented `v2.5.1`
  stretch item, not committed here).
- No standard errors or confidence intervals on the AR coefficients are
  reported.
- Order selection (AIC/BIC) is not performed — the caller supplies
  `order` explicitly.

# Changelog

- 0.1.0: initial (v2.5.1 — AR/autocorrelation package).
