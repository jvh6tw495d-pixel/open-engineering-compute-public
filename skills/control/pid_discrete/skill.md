---
id: control.pid_discrete
version: 0.1.0
status: experimental
domain: control
title: Discrete PID Controller
---

# Purpose

Position-form discrete PID over aligned reference and measurement series.

# Official methodology

`u = Kp e + Ki dt Σe + Kd Δe/dt` with optional saturation.
