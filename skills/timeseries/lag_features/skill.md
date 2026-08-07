---
id: timeseries.lag_features
version: 0.1.0
status: experimental
domain: timeseries
title: Lag Features
---

# Purpose

Produce lag columns for autoregressive model construction. Given a
1-D series and a list of non-negative lag indices, returns aligned
columns and a target slice `y`. Closed-form NumPy slicing — no iterative
factorisation is involved.

# Official methodology

Method id: `closed_form_lag`. Drops the leading `max(lags)` samples
(unusable as targets) and returns `n - max(lags)` aligned rows.
`method.iterative` is `false`, `converged` is `None` per ADR 0013.

# Applicability limits

- `len(values) > max(lags)`.
- All lag indices non-negative integers.

# Failure conditions

- Empty `values`, empty `lags`, negative lag, or insufficient length.

# Alternative methods

- `timeseries.rolling` for windowed statistics and rolling means, which
  provides a different feature class.

# Known limitations

- No pandas-style `NaN`-padding for drops — front rows are explicitly
  dropped (OEC contract: no silent data fabrication, ADR 0004).

# Changelog

- 0.1.0: initial (v2.3 Wave A — TS lag/window features).