"""Evolutionary Compute contracts and result DTOs (ADR 0031).

Algorithms live in ``oec.kernel.evolutionary``; pymoo is an optional extra
(``oec[evolutionary]``). This package is importable without pymoo.
"""

from __future__ import annotations

from oec.evolutionary.contracts import (
    AlgorithmName,
    BudgetSpec,
    BuiltInProblemName,
    EvolutionaryAlgorithmSpec,
    EvolutionaryProblemSpec,
    VariableSpec,
)
from oec.evolutionary.results import EvolutionaryResult

__all__ = [
    "AlgorithmName",
    "BudgetSpec",
    "BuiltInProblemName",
    "EvolutionaryAlgorithmSpec",
    "EvolutionaryProblemSpec",
    "EvolutionaryResult",
    "VariableSpec",
]
