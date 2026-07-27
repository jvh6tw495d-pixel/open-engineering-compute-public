---
id: control.kalman_filter
version: 0.2.0
status: experimental
domain: control
title: Discrete Linear Kalman Filter
---

# Purpose

Discrete time-invariant linear Kalman filter with covariance hygiene.

# Official methodology

Method id: `discrete_linear_kalman_joseph` v0.2.0.

- Predict/update with constant A,B,C,Q,R.
- Q,P0 must be symmetric PSD; R symmetric PD.
- Innovation system solved via ``numpy.linalg.solve`` (no raw inv).
- Joseph form covariance update; soft PSD projection after each step.
- Returns filtered states, innovations, gains, and P sequences.

# Applicability limits

- Linear Gaussian model as declared.
- Finite measurements.
- Not for nonlinear / EKF / UKF.

# Failure conditions

- Non-symmetric or non-PSD/PD covariances.
- Singular or extremely ill-conditioned innovation covariance
  (structured error, not bare LinAlgError).

# What not to use this for

- Non-linear dynamics without extension.
- Claiming optimality under model mismatch.

# Changelog

- 0.2.0: Joseph form, PSD checks, structured numerical errors (B23-01).
- 0.1.0: initial Wave B.
