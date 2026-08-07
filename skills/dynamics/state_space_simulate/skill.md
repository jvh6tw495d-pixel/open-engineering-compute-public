---
id: dynamics.state_space_simulate
version: 0.1.0
status: experimental
domain: dynamics
title: LTI State-Space Simulate
---

# Purpose

Simulate an LTI state-space model under a sampled input sequence.

# Official methodology

Discrete: `x⁺=Ax+Bu`, `y=Cx+Du`. Continuous: ZOH via matrix exponential then same.
