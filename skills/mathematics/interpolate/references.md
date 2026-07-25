# References — mathematics.interpolate

1. Burden, R. L., Faires, J. D. (2011). *Numerical Analysis*, 9th ed.,
   Brooks/Cole, Chapter 3. — piecewise polynomial interpolation, cubic
   splines, and the role of boundary conditions (including not-a-knot).
2. Fritsch, F. N., Carlson, R. E. (1980). Monotone Piecewise Cubic
   Interpolation. *SIAM Journal on Numerical Analysis*, 17(2), 238–246.
   — source of the PCHIP construction used by
   `scipy.interpolate.PchipInterpolator`.
3. SciPy / NumPy documentation:
   [`numpy.interp`](https://numpy.org/doc/stable/reference/generated/numpy.interp.html),
   [`scipy.interpolate.CubicSpline`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.CubicSpline.html),
   [`scipy.interpolate.PchipInterpolator`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.PchipInterpolator.html) —
   the underlying implementations this skill wraps.
4. Independent reference values for golden cases come from closed-form
   evaluation of the sampled function itself (`math.sin`, exact
   polynomials `y = 2x` and `y = x**3`) — never from re-running the
   SciPy interpolant under test (plan section 22: golden values must
   not be derived from the same code path being tested).
