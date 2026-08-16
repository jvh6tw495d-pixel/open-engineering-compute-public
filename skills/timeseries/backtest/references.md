# References — timeseries.backtest

1. Hyndman, R. J., Athanasopoulos, G. (2018). *Forecasting: Principles
   and Practice*, 2nd ed., OTexts, Chapter 5 — rolling-origin evaluation
   procedures, MAE / RMSE aggregates, and the naive baseline skill score.
2. Closed-form sanity reference (golden case below): the one-step naive
   backtest of a constant series `[7, 7, 7, 7]` over steps_ahead 1 has every
   error equal to 0, so both MAE and RMSE are zero, and the naive
   baseline MAE is also zero (so the skill score is defined to be zero).
