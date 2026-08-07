# References — timeseries.pacf

1. Durbin, J. (1960). "The Fitting of Time-Series Models." *Revue de
   l'Institut International de Statistique* 28(3), 233-244 — the
   recursion whose reflection coefficients define the PACF.
2. Box, G. E. P., Jenkins, G. M., Reinsel, G. C., Ljung, G. M. (2015).
   *Time Series Analysis: Forecasting and Control*, 5th ed., Wiley, Ch. 3
   — PACF as a model-order identification tool; the guarantee that the
   biased-ACF-fed recursion never hits a non-positive-definite stop.
3. Hand-derived closed-form case used in the golden tests: for
   `series = [1, -1, 1, -1]` the biased ACF is `[1, -0.75, 0.5, -0.25]`
   (see `timeseries.autocorrelation`'s references.md). Running the
   Levinson-Durbin recursion by hand on that sequence (`k=1`:
   `phi=-0.75`; `k=2`: `phi=-1/7`; `k=3`: `phi=1/6` — full derivation in
   `tests/unit/test_kernel_timeseries_ar.py::TestLevinsonDurbin`) gives
   `pacf = [1, -0.75, -1/7, 1/6]`.
