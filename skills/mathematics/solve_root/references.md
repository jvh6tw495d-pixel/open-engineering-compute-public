# References — mathematics.solve_root

1. Brent, R. P. (1973). *Algorithms for Minimization Without
   Derivatives*. Prentice-Hall, Chapter 4. — source of the algorithm
   behind `method: brentq`.
2. Burden, R. L., Faires, J. D. (2011). *Numerical Analysis*, 9th ed.,
   Brooks/Cole, Chapter 2. — bisection, Newton, and secant methods,
   convergence order proofs, and the `x**3 - x - 2` worked example used
   in this skill's golden cases.
3. SciPy documentation:
   [`scipy.optimize.brentq`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html),
   [`bisect`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.bisect.html),
   [`newton`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.newton.html) —
   the underlying implementations this skill wraps
   (`oec.kernel.numerics.root_finding`).
4. mpmath documentation:
   [`mpmath.findroot`](https://mpmath.org/doc/current/calculus/optimization.html) —
   independent, arbitrary-precision root finder used to compute this
   skill's golden-case reference values (a different implementation
   than SciPy's, per plan section 22: golden values must not be derived
   from the same code path being tested).
