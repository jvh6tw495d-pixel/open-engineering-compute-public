# References — linear.residual_norms

1. NumPy documentation:
   [`numpy.linalg.norm`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html) —
   the canonical vector-norm reference; this skill calls NumPy directly
   (no reimplementation, ADR 0008).
2. Golub, G. H., Van Loan, C. F. (2013). *Matrix Computations*, 4th ed.,
   Johns Hopkins University Press, §2.3 — the L1, L2, and L∞ vector
   norms as closed-form expressions used here for golden cases: the
   unit vector `[3, 0, 0, 4]` has independently-known norms 7, 5, 4.