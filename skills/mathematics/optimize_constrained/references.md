# References — mathematics.optimize_constrained

1. Nocedal, J., Wright, S. J. (2006). *Numerical Optimization*, 2nd ed.,
   Springer, Chapter 18. — source of the SQP algorithm behind
   `method: SLSQP`.
2. Himmelblau, D. M. (1972). *Applied Nonlinear Programming*.
   McGraw-Hill. — source of the four-minima test function
   `(x²+y-11)² + (x+y²-7)²` used in this skill's multi-minima golden
   cases; the four minima's coordinates are a standard, independently
   documented result, not derived from this skill or from SciPy.
3. SciPy documentation:
   [`scipy.optimize.minimize`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html)
   (`method='SLSQP'`, `method='trust-constr'`) — the underlying
   implementations this skill wraps
   (`oec.kernel.optimization.constrained`).
