---
id: timeseries.autocorrelation
version: 0.1.0
status: experimental
domain: timeseries
title: Sample Autocorrelation Function (ACF)
---

# Purpose

Compute the sample autocorrelation function of a 1-D series at lags
`0..nlags`. OEC provides the skill contract; the estimator is a direct,
closed-form NumPy computation — no SciPy/statsmodels dependency exists for
this in the project (ADR 0008 governs wrapping existing solvers; this
closed-form sum has no existing solver to wrap).

# Official methodology

Method id: `sample_acf`. For a (optionally demeaned) series `y` of length
`n`:

- `method="biased"`: `r_k = (sum_{t=0}^{n-k-1} y_t y_{t+k}) / (sum_t y_t^2)`
  — dividing both the lag-`k` cross-sum and the lag-0 sum by `n` cancels,
  so the implementation works with the unnormalized sums directly. This is
  the estimator guaranteed to produce a positive-semidefinite sequence
  (Box, Jenkins & Reinsel §2.1), which is why `timeseries.pacf` and
  `timeseries.ar_yule_walker` always use it internally regardless of what
  a caller of *this* skill requests.
- `method="unbiased"` (a.k.a. "adjusted"): the lag-`k` cross-sum is
  divided by `n-k` instead of `n` before normalizing by the (still
  `n`-normalized) lag-0 sum. Not guaranteed positive-semidefinite for
  small samples or high lags — see `references.md` and
  `timeseries.levinson_durbin`'s failure-mode handling.

`method.iterative` is `false`: one direct computation, deterministic per
ADR 0004. `converged` is `None` per the ADR 0013 amendment (exact, not
iterative).

# Applicability limits

- `series` must be a 1-D array of at least 2 finite numbers.
- `nlags` must satisfy `1 <= nlags < len(series)`.
- `series` must have nonzero variance (a constant series has an undefined
  autocorrelation — division by zero).

# Failure conditions

- `nlags >= len(series)`: rejected by validation before execution.
- Zero-variance (constant) series: rejected by validation before execution.

# Alternative methods

- `timeseries.pacf` for the partial (not raw) autocorrelation.
- `timeseries.ar_yule_walker` to fit an AR model directly from a series,
  without inspecting the ACF yourself.

# Known limitations

- No confidence-interval / significance banding (e.g. the usual
  `+-1.96/sqrt(n)` white-noise bounds) — a caller wanting significance
  testing must compute it from `n` themselves for now.
- FFT-accelerated computation for very long series is not implemented;
  the direct O(n·nlags) sum is used.

# Changelog

- 0.1.0: initial (v2.5.1 — AR/autocorrelation package).
