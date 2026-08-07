---
id: optimization.cvar_lp
version: 0.1.0
status: experimental
domain: optimization
title: Linear CVaR (Rockafellar-Uryasev)
---

# Purpose

Minimize Conditional Value-at-Risk (CVaR) of a linear loss over finite scenarios.

# Official methodology

Method id: `rockafellar_uryasev_cvar`. Auxiliary VaR level t and excesses
u_s >= loss_s(x) - t; objective t + 1/((1-α)S) Σ u_s.

# Applicability limits

- Finite discrete scenarios; continuous decisions.
- sense=min only in v0.
- Requires HiGHS.
