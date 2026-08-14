# References — timeseries.forecast_simple

1. Hyndman, R. J., Athanasopoulos, G. (2018). *Forecasting: Principles
   and Practice*, 2nd ed., OTexts, Chapter 3 — naive, seasonal-naive and
   mean forecasters used as benchmark baselines.
2. Closed-form sanity reference (golden case below): the naive forecast of
   `[1, 2, 3, 4]` over steps_ahead 2 is `[4, 4]` by definition; the
   seasonal-naive forecast with `period = 2` over steps_ahead 3 is
   `[4, 3, 4]` (repeating the last full period).
