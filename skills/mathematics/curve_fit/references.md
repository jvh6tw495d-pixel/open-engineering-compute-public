# References — mathematics.curve_fit

1. Levenberg, K. (1944). *A Method for the Solution of Certain
   Non-Linear Problems in Least Squares*. Quarterly of Applied
   Mathematics, 2(2), 164-168. — source of the algorithm behind
   `method: lm`.
2. Marquardt, D. W. (1963). *An Algorithm for Least-Squares Estimation
   of Nonlinear Parameters*. SIAM Journal on Applied Mathematics,
   11(2), 431-441. — the damping-parameter refinement that completes
   Levenberg-Marquardt.
3. Branch, M. A., Coleman, T. F., Li, Y. (1999). *A Subspace, Interior,
   and Conjugate Gradient Method for Large-Scale Bound-Constrained
   Minimization Problems*. SIAM Journal on Scientific Computing,
   21(1), 1-23. — source of the trust region reflective algorithm
   behind `method: trf`.
4. SciPy documentation:
   [`scipy.optimize.curve_fit`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html) —
   the underlying implementation this skill wraps
   (`oec.kernel.optimization.curve_fit`).
