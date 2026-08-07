# References — timeseries.levinson_durbin

1. Levinson, N. (1947). "The Wiener RMS (Root Mean Square) Error
   Criterion in Filter Design and Prediction." *Journal of Mathematics
   and Physics* 25(1-4), 261-278 — the original recursion.
2. Durbin, J. (1960). "The Fitting of Time-Series Models." *Revue de
   l'Institut International de Statistique* 28(3), 233-244 — the
   time-series application and the reflection-coefficient interpretation.
3. Golub, G. H., Van Loan, C. F. (2013). *Matrix Computations*, 4th ed.,
   Johns Hopkins University Press, §4.7 — the Toeplitz-solve complexity
   argument (`O(p^2)` vs. `O(p^3)` for a general solve).
4. Hand-derived closed-form cases used in the golden tests:
   - Exact AR(1) geometric sequence `[1, 0.5, 0.25, 0.125]` (`r_k =
     0.5^k`) recovers `ar_coefficients = [0.5, 0, 0]` and
     `reflection_coefficients = [0.5, 0, 0]` exactly — a textbook
     property of fitting a higher order to an exact low-order process.
   - `[1, 1.5]` is not a valid autocorrelation sequence
     (`|r1/r0| = 1.5 > 1`, impossible by Cauchy-Schwarz for a real
     process); the recursion stops at `order_reached=0`,
     `is_positive_definite=false`.
   Full derivations in
   `tests/unit/test_kernel_timeseries_ar.py::TestLevinsonDurbin`.
