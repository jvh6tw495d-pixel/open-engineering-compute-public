---
id: uncertainty.propagate_linear
version: 0.1.0
status: experimental
domain: uncertainty
title: Linear Uncertainty Propagation
---

# Purpose

First-order (delta-method) uncertainty propagation: `Σ_y = J Σ_x Jᵀ`.

# Official methodology

Method id: `linear_delta_method`. Jacobian may be a gradient or matrix.
