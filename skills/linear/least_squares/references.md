# References — linear.least_squares

1. NumPy documentation:
   [`numpy.linalg.lstsq`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html) —
   the LAPACK `gelss`/`gelsd` driver this skill wraps; OEC only translates
   structured inputs and maps solver status, it does not reimplement the
   algorithm (ADR 0008).
2. Golub, G. H., Van Loan, C. F. (2013). *Matrix Computations*, 4th ed.,
   Johns Hopkins University Press, §5.3 — the least-squares normal
   equations and the conditioning behaviour that `rank` /
   `singular_values` report.
3. Press, W. H. et al. (2007). *Numerical Recipes*, 3rd ed., Chapter 15 —
   closed-form derivations used here for golden cases: the linear
   regression `y = 2x + 1` fitted on three exact samples yields the unique
   minimum-norm solution `[2, 1]` with zero residual.

4. mpmath closed form: `lstsq([[1, 0], [1, 1], [1, 2]], [1, 3, 5])` has
   analytical solution `x = [1, 2]` independent of any LAPACK call
   (manually verifiable from the normal equations `A^T A x = A^T b`).
