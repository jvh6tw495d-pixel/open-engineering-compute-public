---
id: neural.architecture_vary
version: 0.1.0
status: experimental
domain: neural
title: Architecture IR mutate / crossover
---

# Architecture IR vary

Closed mutation (`widen`, `deepen`, `swap_activation`) and crossover
(`one_point_chain`) over `ArchitectureGraph`. No free Python fitness,
no TITAN. Offspring that fail `validate_for_backend` are rejected.
