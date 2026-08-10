---
id: evolutionary.benchmark
version: 0.1.0
status: experimental
domain: evolutionary
title: Evolutionary Benchmark Harness (X1 thin)
---

# Evolutionary Benchmark (X1 thin)

Compare algorithms on the **same** problem, budget, and seeds.

- `mode=single` — sphere / rosenbrock / rastrigin
- `mode=multi` — zdt1 / zdt2 / bi_sphere

Requires `oec[evolutionary]`. Ranking is **not** a universal claim of
superiority — only evidence under the declared budget (ADR 0031 / X1).
