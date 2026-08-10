"""Hybrid neural + evolutionary pipelines (X2).

Surrogate proposals are never accepted as engineering truth without
high-fidelity re-evaluation on the true objective (ADR 0031 / X2 rule).
"""

from __future__ import annotations

from oec.kernel.hybrid.hyperparams import evo_hyperparameter_search
from oec.kernel.hybrid.surrogate import surrogate_then_evolve

__all__ = [
    "evo_hyperparameter_search",
    "surrogate_then_evolve",
]
