---
id: statistics.bootstrap
version: 0.1.0
status: experimental
domain: statistics
title: Bootstrap Confidence Interval
---

# Purpose

Nonparametric percentile bootstrap confidence interval for a sample
statistic (mean / median / variance). Deterministic when a `seed` is
supplied (per ADR 0004).

# Official methodology

Method id: `percentile_bootstrap`. Resamples with replacement, evaluates
the statistic on each resample, and takes the empirical
`(alpha/2, 1 - alpha/2)` quantiles of the bootstrap distribution.

# Applicability limits

- `n_samples >= 1`.
- `n_resamples >= 1` (and large enough for stable quantiles — typically
  `>= 1000`).
- Optional `seed` makes the result deterministic; without it, this skill
  is non-deterministic and the execution policy `deterministic: true`
  applies *only* once a `seed` is supplied.

# Failure conditions

- Empty sample.
- Unsupported statistic kind.

# Alternative methods

- `statistics.intervals` for the parametric Student-t CI of the mean.

# Known limitations

- Percentile bootstrap (not BCa); better bias correction is a v2.4
  candidate.

# Changelog

- 0.1.0: initial (v2.3 Wave A — bootstrap, regression, intervals).
