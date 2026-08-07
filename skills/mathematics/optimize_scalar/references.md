# References — mathematics.optimize_scalar

1. Brent, R. P. (1973). *Algorithms for Minimization Without
   Derivatives*. Prentice-Hall, Chapter 5. — source of the algorithm
   behind `method: bounded`/`brent`.
2. Press, W. H., Teukolsky, S. A., Vetterling, W. T., Flannery, B. P.
   (2007). *Numerical Recipes*, 3rd ed., Cambridge University Press,
   Sections 10.2 (golden-section search) and 10.3 (Brent's method) —
   the algorithms this skill wraps, and the closed-form derivative test
   (`f'=0`, sign of `f''`) used to independently derive the multi-minima
   golden case's expected values.
3. SciPy documentation:
   [`scipy.optimize.minimize_scalar`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize_scalar.html) —
   the underlying implementation this skill wraps
   (`oec.kernel.optimization.scalar`).
