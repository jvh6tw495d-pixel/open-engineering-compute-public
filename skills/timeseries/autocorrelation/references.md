# References — timeseries.autocorrelation

1. Box, G. E. P., Jenkins, G. M., Reinsel, G. C., Ljung, G. M. (2015).
   *Time Series Analysis: Forecasting and Control*, 5th ed., Wiley, §2.1 —
   definition of the sample ACF, biased vs. unbiased ("adjusted")
   normalization, and why the biased estimator is the one guaranteed to
   produce a positive-semidefinite (i.e. Toeplitz-solvable) sequence.
2. Hamilton, J. D. (1994). *Time Series Analysis*, Princeton University
   Press, §3.4 — sample autocovariance/autocorrelation and its asymptotic
   properties.
3. Hand-derived closed-form case used in the golden tests: for
   `series = [1, -1, 1, -1]` (already zero-mean), `c0 = sum(y^2) = 4`;
   `raw_1 = y0*y1 + y1*y2 + y2*y3 = -1-1-1 = -3` so the biased
   `acf[1] = -3/4 = -0.75`; `raw_2 = y0*y2 + y1*y3 = 1+1 = 2` so
   `acf[2] = 2/4 = 0.5`; `raw_3 = y0*y3 = -1` so `acf[3] = -1/4 = -0.25`.
   Verifiable by hand from the definition alone.
