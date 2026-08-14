---
id: linear.residual_norms
version: 0.1.0
status: experimental
domain: linear
title: Residual Norms (L1, L2, Linf)
---

# Purpose

Compute the L1, L2, and L∞ norms of a residual vector. Often used
post-execution as a structured measure of fit error. OEC provides the
skill contract; numerical merit belongs to NumPy as documented in
references.

# Official methodology

Method id: `numpy_vector_norms`. Direct, closed-form vector reduction —
one call, deterministic per ADR 0004. No iterative factorisation is
involved, so `method.iterative` is `false` and `converged` is `None`
per ADR 0013 amendment.

# Applicability limits

- Input `r` must be a non-empty 1-D array of finite numbers.

# Failure conditions

- `r` is empty, not a list, or contains non-number entries.

# Alternative methods

- For a full `A x ≈ b` least-squares fit (solution plus residual vector)
  see `linear.least_squares`, which can be combined with this skill.

# Known limitations

- No weighted norms; future `linear.residual_norms.weighted` is a v2.4
  candidate.

# Changelog

- 0.1.0: initial (v2.3 Wave A — residual norms reporting enrichment).
