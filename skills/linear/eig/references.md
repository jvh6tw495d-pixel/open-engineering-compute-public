# References — linear.eig

1. NumPy documentation:
   [`numpy.linalg.eig`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eig.html) —
   the underlying LAPACK `geev` implementation this skill wraps; OEC only
   translates structured inputs and maps solver status.
2. Golub, G. H., Van Loan, C. F. (2013). *Matrix Computations*, 4th ed.,
   Johns Hopkins University Press, Chapter 7 — the unsymmetric eigenvalue
   problem and the conventions this skill preserves (eigenvalues as
   parallel real/imag lists, right-eigenvector columns).
3. Press, W. H. et al. (2007). *Numerical Recipes*, 3rd ed., Chapter 11 —
   the closed-form eigendecomposition of the diagonal matrix
   `diag([1, 2, 3])` used as the golden-case reference value (a value
   derivable independently of any LAPACK call).