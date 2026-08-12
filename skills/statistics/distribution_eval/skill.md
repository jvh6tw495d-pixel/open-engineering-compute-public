---
id: statistics.distribution_eval
version: 0.1.0
status: experimental
domain: statistics
title: Distribution Evaluation (PDF/CDF/PPF/Sample)
---

# Purpose

Evaluate closed-catalog probability distributions (PDF, CDF, PPF, mean, std,
sample) via SciPy. OEC governs the contract; SciPy owns statistical merit.

# Official methodology

Method id: `scipy_stats_distribution`.

Allowed distributions: `norm`, `t`, `uniform`, `expon`, `chi2`, `beta`.
Allowed operations: `pdf`, `cdf`, `ppf`, `mean`, `std`, `sample`.

# Changelog

- 0.1.0: W1-MVP initial.
