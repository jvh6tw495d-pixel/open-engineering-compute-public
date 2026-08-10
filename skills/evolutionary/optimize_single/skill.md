---
id: evolutionary.optimize_single
version: 0.1.0
status: experimental
domain: evolutionary
title: Single-Objective Evolutionary Optimize (pymoo)
---

# Single-Objective Evolutionary Optimize

Box-constrained single-objective search via **pymoo**. Objectives:

- built-in test problems (`sphere`, `rosenbrock`, `rastrigin`), **or**
- closed **expression IR** trees (same operator allow-list as GP);

optional **inequality constraints** `g(x) ≤ 0` via IR; optional **multi-seed**
matrix (`seeds: [0,1,2]` → mean/std report). Requires
`uv sync --extra evolutionary`.

No user Python fitness functions (ADR 0031 / Part B).
