---
id: uncertainty.morris
version: 0.1.0
status: experimental
domain: uncertainty
title: Morris Elementary Effects
---

# Purpose

Morris elementary-effects **screen for a declared linear model**
``f(x) = intercept + coeffs·x`` on a hyper-rectangle.

# Official methodology

Method id: ``morris_linear_screen`` (not black-box Morris, not Sobol).

- Classic even ``n_levels >= 4``.
- Elementary effects are Δf/Δx_j in **physical units of the linear model**.
- For a truly linear f, μ approaches the coefficient.

# Hypotheses

- Model is exactly linear in the declared coefficients.
- Factors vary independently inside the given bounds.

# What not to use this for

- Global sensitivity / Sobol indices of a nonlinear black-box.
- Claiming factor importance beyond the declared linear structure.

# References

1. Morris (1991), Technometrics — factorial sampling plans.
2. Saltelli et al. — Global Sensitivity Analysis (contrast: this skill is linear-only).
