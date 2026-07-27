---
id: uncertainty.propagate_linear
version: 0.1.0
status: experimental
domain: uncertainty
title: Linear Uncertainty Propagation
---

# Purpose

First-order (delta-method) uncertainty propagation ``Σ_y = J Σ_x Jᵀ``.

# Official methodology

- Jacobian gradient (scalar y) or matrix (vector y).
- Covariance must be symmetric PSD.
- Optional ``nominal`` (length n) is **provenance** and yields
  ``nominal_output = J @ nominal`` when provided (B23-02).

# What not to use this for

- Highly nonlinear maps without checking remainder.
- Non-Gaussian tail risk (prefer scenario/CVaR tools).

# References

1. Standard engineering error-propagation / delta method.
