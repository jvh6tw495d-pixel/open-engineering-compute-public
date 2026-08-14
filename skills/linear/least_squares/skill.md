---
id: linear.least_squares
version: 0.1.0
status: experimental
domain: linear
title: Least Squares Solver
---

# Purpose

Solve `A @ x ≈ b` in the least-squares sense for any real matrix `A`
(square, overdetermined, or rank-deficient). OEC provides the skill
contract; numerical merit belongs to NumPy/LAPACK (`gelss`/`gelsd`).

# Official methodology

Method id: `numpy_lstsq`. Single `numpy.linalg.lstsq` call with
`rcond=None` (default = `finfo.float.eps * max(M,N) * 4`). Returns the
minimum-norm solution when the system is rank-deficient, and the residual
vector `b - A x`. Residual sum of squares is `None` when NumPy cannot
compute it (square systems or rank-deficient rectangular systems) — the
skill does not fabricate one in that case.

`method.iterative` is `false`: one LAPACK call, deterministic per ADR
0004. `converged` is `None` per ADR 0013 amendment (exact, not iterative).

# Applicability limits

- `A` must be a 2-D non-empty array of finite numbers.
- `b` must be a 1-D vector with `len(b) == len(A)`.

# Failure conditions

- Mismatched `A` rows and `b` length.
- Non-finite entries propagate from LAPACK; the validator flags dimension
  mismatch before factorisation.

# Alternative methods

- `linear.solve_system` for square well-conditioned problems where the
  residual is expected to be exactly zero.

# Known limitations

- No Bayesian priors, no Tikhonov regularisation — a v2.4 `linear.ridge`
  skill will cover those.

# Changelog

- 0.1.0: initial (v2.3 Wave A — least squares, residual norms, condition
  reporting).
