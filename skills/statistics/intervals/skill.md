---
id: statistics.intervals
version: 0.1.0
status: experimental
domain: statistics
title: Confidence Interval for the Mean
---

# Purpose

Two-sided confidence interval for the population mean of a numeric
sample. Defaults to Student-t (`df = n - 1`); falls back to the Gaussian
interval when `known_variance` is true.

# Official methodology

Method id: `student_t_gaussian_ci`. Single-pass sample mean and sample
standard deviation (ddof=1) via NumPy; quantile lookups via SciPy
`stats.t`/`stats.norm`. Closed-form formulas from Montgomery & Runger
§8. `method.iterative` is `false` and `converged` is `None` per ADR 0013
amendment (one call, exact).

# Applicability limits

- `samples` must be a non-empty 1-D array of finite numbers.
- Student-t requires `n >= 2`; the Gaussian option supports `n == 1`
  (though the CI is then zero, since `s = 0`).

# Failure conditions

- Empty sample.
- `confidence_level` outside `(0, 1)`.
- fewer than 2 samples in the student-t mode.

# Alternative methods

- `statistics.bootstrap` for nonparametric intervals robust to non-normal
  sample distributions.

# Known limitations

- Symmetric intervals only; asymmetric / one-sided bounds are v2.4+
  candidates.

# Changelog

- 0.1.0: initial (v2.3 Wave A — statistics intervals).