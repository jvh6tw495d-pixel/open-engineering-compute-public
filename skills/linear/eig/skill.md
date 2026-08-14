---
id: linear.eig
version: 0.1.0
status: experimental
domain: linear
title: Eigenvalues and Eigenvectors
---

# Purpose

Compute eigenvalues and right eigenvectors of a square matrix.
OEC provides the skill contract; numerical merit belongs to NumPy/LAPACK
as documented in references.

# Official methodology

Method id: `numpy_eig`. Calls `numpy.linalg.eig` (LAPACK `geev`) and
returns complex eigenvalues split into parallel real/imag lists, and the
right-eigenvector matrix as a list of columns (column `j` is the
eigenvector for eigenvalue `j`). Iterative factorisation is treated as
not iterative from OEC's contract point of view — one call, deterministic
per ADR 0004 — so `method.iterative` is `false` and `converged` is `None`
per ADR 0013 amendment.

# Applicability limits

- Input must be a non-empty square 2D array of finite numbers.
- Eigenvector decomposition is undefined for non-square inputs and is
  rejected by JSON Schema and the math validator.

# Failure conditions

- Non-square matrix.
- Empty matrix.
- Non-finite entries propagate from LAPACK; the validator flags shape
  errors before factorisation.

# Alternative methods

- `linear.matrix_properties` (eigenvalues only, no eigenvectors).
- For symmetric / Hermitian matrices one would prefer a future
  `linear.eigh` skill (v2.4 candidate).

# Known limitations

- Eigenvectors are reported as-is from LAPACK and are unique only up to
  scale; this skill does not normalise them.

# Changelog

- 0.1.0: initial (v2.3 Wave A — linear eig full API skill).
