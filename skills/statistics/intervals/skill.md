---
id: statistics.intervals
version: 0.2.0
status: experimental
domain: statistics
title: Confidence Interval for the Mean
---

# Purpose

Two-sided confidence interval for the population mean of a numeric sample.

# Official methodology

Method id: `student_t_gaussian_ci` v0.2.0.

- **Student-t** (default): uses sample standard deviation with ``df = n - 1``
  when ``population_standard_deviation`` is omitted. Requires ``n >= 2``.
- **Normal / Z**: when ``population_standard_deviation`` (known population σ)
  is a finite positive number. Valid for any ``n >= 1``.

Output field ``dispersion_used`` records which dispersion entered the formula.

# Applicability limits

- ``samples``: non-empty 1-D finite numbers.
- ``confidence_level`` ∈ (0, 1).
- Do **not** claim “known variance” without supplying population σ.

# Failure conditions

- Empty or non-finite samples.
- Student-t with ``n < 2``.
- Non-positive or non-finite ``population_standard_deviation``.
- Removed field ``known_variance`` (error).

# What not to use this for

- Non-normal heavy-tailed data without justification (prefer bootstrap).
- Variance estimation itself (this skill estimates a CI on the **mean** only).

# Alternative methods

- ``statistics.bootstrap`` for nonparametric intervals.

# Changelog

- 0.2.0: replace ambiguous ``known_variance`` with ``population_standard_deviation``;
  report ``dispersion_used`` (A23-01).
- 0.1.0: initial Wave A.
