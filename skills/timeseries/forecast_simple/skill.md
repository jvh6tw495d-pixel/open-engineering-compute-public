---
id: timeseries.forecast_simple
version: 0.1.0
status: experimental
domain: timeseries
title: Simple Forecasters (Naive, Mean, Seasonal)
---

# Purpose

Three benchmark forecasters over a lead window. Naive (last value persists),
mean (historical mean persists), and seasonal-naive (last full-cycle
observation for that phase).

# Official methodology

Method id: `closed_form_forecast`. No iterative factorisation; closed
form, deterministic per ADR 0004. `converged` is `None` per ADR 0013
amendment.

# Applicability limits

- `series` non-empty 1-D float array.
- `steps_ahead >= 1`.
- `method == seasonal_naive` requires `series.size >= period` and
  `period >= 1`.

# Failure conditions

- Unsupported `method`.
- Missing `period` for `seasonal_naive`.
- Insufficient series length for a seasonal forecast.

# Alternative methods

- `timeseries.backtest` evaluates the forecasters on held-out data.

# Known limitations

- No confidence intervals — confidence envelopes appear in v2.4 candidate
  `timeseries.forecast_probabilistic`.

# Changelog

- 0.1.0: initial (v2.3 Wave A — simple forecast + backtest hook).
