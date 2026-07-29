# References — timeseries.ar_yule_walker

1. Yule, G. U. (1927). "On a Method of Investigating Periodicities in
   Disturbed Series." *Philosophical Transactions of the Royal Society
   A* 226, 267-298 — the original Yule-Walker equations.
2. Box, G. E. P., Jenkins, G. M., Reinsel, G. C., Ljung, G. M. (2015).
   *Time Series Analysis: Forecasting and Control*, 5th ed., Wiley, §3.3
   — Yule-Walker estimation, its consistency, and its relationship to
   the Levinson-Durbin recursion.
3. Hand-derived closed-form case used in the golden tests: for
   `series = [1, -1, 1, -1]` (zero mean), `order=1` gives `acf_used =
   [1, -0.75]`, `ar_coefficients = [-0.75]` (`phi = r1/r0`),
   `sample_variance = c0/n = 4/4 = 1.0`, and `innovation_variance =
   sample_variance * E1 = 1.0 * (1 - 0.75^2) = 0.4375`. Full derivation
   in `tests/unit/test_kernel_timeseries_ar.py::TestArYuleWalker`.
