---
id: uncertainty.propagate_linear
version: 0.2.0
status: experimental
domain: uncertainty
title: Linear Uncertainty Propagation
---

# Purpose

First-order (delta-method) uncertainty propagation ``Σ_y = J Σ_x Jᵀ``.

# Official methodology

- Jacobian gradient (scalar y) or matrix (vector y).
- Covariance must be symmetric PSD.
- Optional ``nominal`` (length n, finite) is provenance; when provided the
  runtime also returns ``nominal_output = J @ nominal`` (B23-02).
- Without ``nominal``, ``nominal_output`` is omitted (not null).

# What not to use this for

- Highly nonlinear maps without checking remainder.
- Non-Gaussian tail risk (prefer scenario/CVaR tools).

# Changelog

- 0.2.0: schema admits ``nominal_output``; nominal length/finite checks.
- 0.1.0: initial Wave B.

# References

1. Standard engineering error-propagation / delta method.
