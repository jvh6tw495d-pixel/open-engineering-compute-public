---
id: hybrid.surrogate_optimize
version: 0.1.0
---

# Surrogate + Evolutionary + High-Fidelity Verify (X2)

1. Sample true built-in objective (stand-in for expensive simulator)
2. Train MLP surrogate (`oec[neural]`)
3. Optimize surrogate with Nevergrad (`oec[evolutionary]`)
4. **Re-evaluate on true f** — surrogate optimum is never engineering truth

Requires both extras: `uv sync --extra neural --extra evolutionary`.
