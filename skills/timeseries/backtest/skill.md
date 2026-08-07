---
id: timeseries.backtest
version: 0.1.0
status: experimental
domain: timeseries
title: Backtest (rolling, simple forecasters)
---

# Purpose

Rolling one-step backtest of the simple forecasters in
`timeseries.forecast_simple`. Reports per-window errors and an aggregate
MAE/RMSE plus a naive-baseline skill score. This is the backtest hook
called for in the v2.3 Wave A timeseries backlog (plan section 7).

# Official methodology

Method id: `rolling_simple_backtest`. Walks the last `n_evaluations`
samples, builds a forecast over `steps_ahead` steps from the prefix up to
each sample, and compares the first predicted step to the held-out
actual. Iterative over the windows; `converged: None` per ADR 0013
("each individual forecasted step is exact; the iteration is over
rolling windows, not a numerical solver"). Scoring is closed form.

# Applicability limits

- `n_evaluations >= 1`.
- `n_series - n_evaluations >= 1` (the first training window must be
  non-empty).
- Forecast `method` restrictions are inherited from
  `timeseries.forecast_simple`.

# Failure conditions

- Args outside the limits above.
- Unsupported `method` / missing `period` for `seasonal_naive`.

# Alternative methods

- Time-series cross-validation in the Hyndman sense (full multi-step window
  evaluation); a v2.4 candidate `timeseries.backtest_expanding` covers
  multi-step multistep scoring.

# Known limitations

- Compares only the first forecast step (one-step-ahead backtest);
  multi-step rolling scoring is the v2.4 candidate above.

# Changelog

- 0.1.0: initial (v2.3 Wave A — backtest hook for simple forecasters).