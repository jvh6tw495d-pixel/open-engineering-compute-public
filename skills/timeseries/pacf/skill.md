---
id: timeseries.pacf
version: 0.1.0
status: experimental
domain: timeseries
title: Sample Partial Autocorrelation Function (PACF)
---

# Purpose

Compute the sample partial autocorrelation function of a 1-D series at
lags `0..nlags`. `pacf[k]` is the correlation between `y_t` and
`y_{t+k}` after removing the linear dependence explained by the
intermediate lags `1..k-1` — the classic tool for choosing an AR model's
order (Box-Jenkins identification).

# Official methodology

Method id: `levinson_durbin_pacf`. The skill first computes the sample
autocorrelation of `series` up to `nlags` using the **biased** estimator
(`oec.kernel.timeseries.ar.autocorrelation`, `method="biased"`) — this is
not a caller choice, because only the biased estimator is guaranteed to
produce a positive-semidefinite sequence — then runs the
`oec.kernel.timeseries.ar.levinson_durbin` recursion. `pacf[0]` is
defined as `1.0` by convention; `pacf[k]` for `k >= 1` is the recursion's
reflection coefficient at lag `k`, which is exactly the partial
autocorrelation at that lag (Durbin, 1960).

Because the ACF this skill feeds into the recursion is always the biased
estimator, `is_positive_definite` is mathematically guaranteed `true` and
`order_reached` guaranteed to equal `nlags` — the skill still reports
both fields explicitly rather than assuming it, so a caller never has to
trust an undocumented invariant.

`method.iterative` is `false`: the recursion runs a fixed, input-size-
determined number of steps — not an iterative solver seeking convergence
(ADR 0013 amendment). `converged` is `None`.

# Applicability limits

- `series` must be a 1-D array of at least 2 finite numbers.
- `nlags` must satisfy `1 <= nlags < len(series)`.
- `series` must have nonzero variance.

# Failure conditions

- `nlags >= len(series)`: rejected by validation before execution.
- Zero-variance (constant) series: rejected by validation before execution.

# Alternative methods

- `timeseries.autocorrelation` for the raw (non-partial) ACF.
- `timeseries.ar_yule_walker` to go directly to fitted AR coefficients at
  a chosen order, rather than inspecting the PACF to choose one yourself.
- `timeseries.levinson_durbin` to run the same recursion directly on an
  already-known autocorrelation/autocovariance sequence.

# Known limitations

- Only the Levinson-Durbin/Yule-Walker PACF estimator is implemented;
  the OLS ("regression") PACF estimator is not.
- No confidence-interval / significance banding is reported.

# Changelog

- 0.1.0: initial (v2.5.1 — AR/autocorrelation package).
