---
id: dynamics.stability_margins
version: 0.2.0
status: experimental
domain: dynamics
title: LTI Stability Margins
---

# Purpose

Classify spectral (pole) stability of a linear state matrix A.

# Official methodology

Method reports **spectral / pole margins only** (B23-04):

- continuous: spectral abscissa max Re(λ); classes stable / marginal / unstable
- discrete: spectral radius max |λ|

Field ``margin_kind`` is always
``spectral_pole_margin_not_gain_phase``.
``classification`` ∈ {stable, marginal, unstable}; ``stable`` is the boolean
for the stable class only.

# What this is NOT

- Classical **gain margin** or **phase margin** of a loop transfer function
- µ-analysis / robust stability margins

# Applicability limits

- Finite square real A.
- Boundary poles classified with ``boundary_tol`` (default 1e-12).

# What not to use this for

- Designing compensators via Bode/Nyquist margins.
- Nonlinear Lyapunov certificates.

# Changelog

- 0.2.0: classification + spectral margin fields (B23-04).
- 0.1.0: initial Wave B.

# References

1. Chen — Linear System Theory (eigenvalue stability).
2. NumPy ``linalg.eigvals``.
