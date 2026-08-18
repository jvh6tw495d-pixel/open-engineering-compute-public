"""Evolutionary kernel — pymoo / DEAP / Nevergrad wrappers (ADR 0031)."""

from __future__ import annotations

from oec.kernel.evolutionary.benchmark import run_benchmark
from oec.kernel.evolutionary.blackbox import blackbox_optimize, optimizer_portfolio
from oec.kernel.evolutionary.errors import (
    DeapNotAvailableError,
    NeatNotAvailableError,
    NevergradNotAvailableError,
    PymooNotAvailableError,
)
from oec.kernel.evolutionary.expression import evaluate_expression
from oec.kernel.evolutionary.gp import run_evolution_strategy, run_genetic_programming
from oec.kernel.evolutionary.hyperneat import run_hyperneat
from oec.kernel.evolutionary.multiobjective import optimize_multi
from oec.kernel.evolutionary.neat import run_neat
from oec.kernel.evolutionary.optimize import optimize_single
from oec.kernel.evolutionary.seed_matrix import run_seed_matrix, run_seed_matrix_multi

__all__ = [
    "DeapNotAvailableError",
    "NeatNotAvailableError",
    "NevergradNotAvailableError",
    "PymooNotAvailableError",
    "blackbox_optimize",
    "evaluate_expression",
    "optimize_multi",
    "optimize_single",
    "optimizer_portfolio",
    "run_benchmark",
    "run_evolution_strategy",
    "run_genetic_programming",
    "run_hyperneat",
    "run_neat",
    "run_seed_matrix",
    "run_seed_matrix_multi",
]
