---
id: control.pid_discrete
version: 0.1.0
status: experimental
domain: control
title: Discrete PID Controller
---

# Purpose

Position-form discrete PID on aligned reference and measurement series.

# Official methodology

``u = Kp e + Ki * I + Kd Δe/dt`` with optional output saturation.

# Anti-windup (B23-05)

- ``anti_windup=none`` (default): integrator **continues** under saturation
  (classic windup behaviour — documented, not hidden).
- ``anti_windup=clamp``: freeze integral while unsaturated command is outside
  ``[u_min, u_max]``.

Outputs ``integral_term`` and ``saturated_steps`` for audit.

# What not to use this for

- Continuous-time plant design without discretisation analysis.
- Claiming anti-windup when using ``none``.

# References

1. Åström & Hägglund — PID Controllers.
