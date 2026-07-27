---
id: statistics.regression
version: 0.1.0
status: experimental
domain: statistics
title: Linear Regression (OLS)
---

# Purpose

Ordinary least-squares linear regression of `y` on the columns of a design
matrix `x`. Returns coefficients, fitted values, residuals, R², adjusted
R², RMSE, and residual standard error. OEC provides the skill contract;
the closed-form formulas are from Montgomery & Runger §11.

# Official methodology

Method id: `ols_closed_form`. Single `numpy.linalg.lstsq` call to solve the
normal equations (no iterative factorisation); sum-of-squares, R², and
standard error are computed directly from the residual vector. `x` is the
design matrix (rows = samples, columns = features, no intercept
auto-added) — the caller supplies the all-ones column when an intercept is
needed.

`method.iterative` is `false` (one call, deterministic per ADR 0004);
`converged` is `None` per ADR 0013 amendment.

# Applicability limits

- `n_samples > n_features` (degrees of freedom must be positive).
- `x` rows `== y` length.
- `x` is a non-empty 2D array of finite numbers.

# Failure conditions

- Non-finite entries.
- Mismatched shapes.
- `n_samples <= n_features`.

# Alternative methods

- `linear.least_squares` returns the raw least-squares coefficients
  without the regression summary statistics.

# Known limitations

- No robust standard errors, no Bayesian priors — those are v2.4+
  candidates.
- Multicollinearity inflates `coefficients` variance silently; the
  `linear.matrix_properties` skill can be used to diagnose it.

# Changelog

- 0.1.0: initial (v2.3 Wave A — regression, intervals, bootstrap).