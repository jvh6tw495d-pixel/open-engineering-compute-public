---
id: uncertainty.morris
version: 0.1.0
status: experimental
domain: uncertainty
title: Morris Elementary Effects
---

# Purpose

Morris elementary-effects screening for a linear model
`f(x) = intercept + coeffs·x` on rectangular bounds.

# Official methodology

Method id: `morris_linear_screen`. Reports `mu`, `mu_star`, `sigma` per factor.

# Known limitations

- Linear models only (no arbitrary callables in the sandbox).
