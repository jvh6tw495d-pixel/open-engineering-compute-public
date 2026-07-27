# References — timeseries.lag_features

1. Hyndman, R. J., Athanasopoulos, G. (2018). *Forecasting: Principles
   and Practice*, 2nd ed., OTexts — Chapter 5 (autoregressive models and
   the impact of lag truncation on training rows).
2. NumPy documentation:
   [`numpy.ndarray`](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html) —
   NumPy slicing used to align lag columns and target slice. OEC only
   reshapes explicit indices; no SciPy is reimplemented here.
3. Closed-form sanity reference (golden case below): the lag-1 column of
   `[1, 2, 3, 4]` is `[1, 2, 3]` (length `n - max_lag = 3`), aligned to
   `y = [2, 3, 4]`. Derivable by direct indexing.