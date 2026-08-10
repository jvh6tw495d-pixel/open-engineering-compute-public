"""Evolutionary Compute contracts and result DTOs (ADR 0031).

Algorithms live in ``oec.kernel.evolutionary``; pymoo is an optional extra
(``oec[evolutionary]``). This package is importable without pymoo.
"""

from __future__ import annotations

from oec.evolutionary.contracts import (
    AlgorithmName,
    BenchmarkSpec,
    BudgetSpec,
    BuiltInMultiProblemName,
    BuiltInProblemName,
    EvolutionaryAlgorithmSpec,
    EvolutionaryProblemSpec,
    MultiObjectiveAlgorithmName,
    MultiObjectiveAlgorithmSpec,
    MultiObjectiveProblemSpec,
    VariableSpec,
)
from oec.evolutionary.results import (
    BenchmarkResult,
    EvolutionaryParetoResult,
    EvolutionaryResult,
)

__all__ = [
    "AlgorithmName",
    "BenchmarkResult",
    "BenchmarkSpec",
    "BudgetSpec",
    "BuiltInMultiProblemName",
    "BuiltInProblemName",
    "EvolutionaryAlgorithmSpec",
    "EvolutionaryParetoResult",
    "EvolutionaryProblemSpec",
    "EvolutionaryResult",
    "MultiObjectiveAlgorithmName",
    "MultiObjectiveAlgorithmSpec",
    "MultiObjectiveProblemSpec",
    "VariableSpec",
]
