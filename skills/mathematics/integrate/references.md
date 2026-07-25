# References — mathematics.integrate

1. Burden, R. L., Faires, J. D. (2011). *Numerical Analysis*, 9th ed.,
   Brooks/Cole, Chapter 4. — Newton–Cotes rules (trapezoid, Simpson)
   and composite quadrature error bounds.
2. Piessens, R., de Doncker-Kapenga, E., Überhuber, C. W., Kahaner, D. K.
   (1983). *QUADPACK: A Subroutine Package for Automatic Integration*.
   Springer. — adaptive quadrature underlying `scipy.integrate.quad`.
3. SciPy documentation:
   [`scipy.integrate.quad`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html),
   [`simpson`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.simpson.html),
   [`trapezoid`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.trapezoid.html) —
   the underlying implementations this skill wraps.
4. mpmath documentation:
   [`mpmath.quad`](https://mpmath.org/doc/current/calculus/integration.html) —
   independent, arbitrary-precision integrator used to compute this
   skill's golden-case reference values (a different implementation
   than SciPy's, per plan section 22: golden values must not be derived
   from the same code path being tested). Closed-form integrals
   (e.g. ∫₀^π sin = 2, ∫₀¹ x² = 1/3) are used when available.
