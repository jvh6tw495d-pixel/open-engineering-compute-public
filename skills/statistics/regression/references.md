# References — statistics.regression

1. NumPy documentation:
   [`numpy.linalg.lstsq`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html) —
   the underlying OLS solver used to recover coefficients; OEC only
   translates structured inputs and computes the closed-form summary
   statistics from the residual vector.
2. Montgomery, D. C., Runger, G. C. (2018). *Applied Statistics and
   Probability for Engineers*, 7th ed., Wiley — Chapter 11 (simple linear
   regression, R², adjusted R², residual standard error) and Chapter 12
   (multiple regression).
3. Press, W. H. et al. (2007). *Numerical Recipes*, 3rd ed., Chapter 15 —
   closed-form derivations used here for the golden cases: a noisy but
   exact-fit model `y = 2x + 1` (intercept 1, slope 2) over 4 samples
   gives R² = 1, zero residual, and `coefficients = [1, 2]` independent of
   any LAPACK call.
