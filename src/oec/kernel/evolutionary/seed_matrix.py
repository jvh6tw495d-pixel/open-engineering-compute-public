"""Multi-seed evolutionary matrix (Part B E-D4)."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.evolutionary.contracts import (
    BudgetSpec,
    EvolutionaryAlgorithmSpec,
    EvolutionaryProblemSpec,
    MultiObjectiveAlgorithmSpec,
    MultiObjectiveProblemSpec,
)
from oec.evolutionary.hashing import problem_fingerprint
from oec.evolutionary.runtime import EvolutionaryRuntimeSpec, MultiSeedReport
from oec.kernel.evolutionary.multiobjective import optimize_multi
from oec.kernel.evolutionary.optimize import optimize_single


def run_seed_matrix(
    problem: EvolutionaryProblemSpec,
    algorithm: EvolutionaryAlgorithmSpec,
    runtime: EvolutionaryRuntimeSpec | None = None,
) -> MultiSeedReport:
    """Run the same SOO problem across ``runtime.resolved_seeds()``."""
    rt = runtime or EvolutionaryRuntimeSpec(seed=algorithm.seed, budget=algorithm.budget)
    seeds = rt.resolved_seeds()
    budget = rt.budget or algorithm.budget
    rows: list[dict[str, Any]] = []
    bests: list[float] = []
    evals: list[int] = []
    for seed in seeds:
        algo = EvolutionaryAlgorithmSpec(
            algorithm=algorithm.algorithm,
            budget=BudgetSpec(generations=budget.generations, population=budget.population),
            seed=seed,
        )
        seed_rt = EvolutionaryRuntimeSpec(
            seed=seed,
            budget=budget,
            max_seconds=rt.max_seconds,
            max_evaluations=rt.max_evaluations,
            history=rt.history,
            hv_reference=rt.hv_reference,
        )
        result = optimize_single(problem, algo, runtime=seed_rt)
        bests.append(result.best_objective)
        evals.append(result.n_evaluations)
        rows.append(
            {
                "seed": seed,
                "best_objective": result.best_objective,
                "n_evaluations": result.n_evaluations,
                "n_generations": result.n_generations,
                "feasibility_rate": result.feasibility_rate,
                "best_x": result.best_x,
            }
        )
    arr = np.asarray(bests, dtype=float)
    return MultiSeedReport(
        algorithm=algorithm.algorithm.value,
        seeds=seeds,
        best_objectives=bests,
        mean_best_objective=float(np.mean(arr)),
        std_best_objective=float(np.std(arr)),
        min_best_objective=float(np.min(arr)),
        max_best_objective=float(np.max(arr)),
        mean_n_evaluations=float(np.mean(evals)) if evals else 0.0,
        rows=rows,
        problem_fingerprint=problem_fingerprint(problem.model_dump(mode="json")),
        message="ok",
    )


def run_seed_matrix_multi(
    problem: MultiObjectiveProblemSpec,
    algorithm: MultiObjectiveAlgorithmSpec,
    runtime: EvolutionaryRuntimeSpec | None = None,
) -> dict[str, Any]:
    """Multi-seed multi-objective report (HV mean/std when available)."""
    rt = runtime or EvolutionaryRuntimeSpec(seed=algorithm.seed, budget=algorithm.budget)
    seeds = rt.resolved_seeds()
    budget = rt.budget or algorithm.budget
    rows: list[dict[str, Any]] = []
    hvs: list[float] = []
    for seed in seeds:
        algo = MultiObjectiveAlgorithmSpec(
            algorithm=algorithm.algorithm,
            budget=BudgetSpec(generations=budget.generations, population=budget.population),
            seed=seed,
            n_partitions=algorithm.n_partitions,
        )
        seed_rt = EvolutionaryRuntimeSpec(
            seed=seed,
            budget=budget,
            hv_reference=rt.hv_reference,
        )
        result = optimize_multi(problem, algo, runtime=seed_rt)
        row = {
            "seed": seed,
            "n_nondominated": result.n_nondominated,
            "hypervolume": result.hypervolume,
            "hv_reference": result.hv_reference,
            "n_evaluations": result.n_evaluations,
        }
        rows.append(row)
        if result.hypervolume is not None:
            hvs.append(float(result.hypervolume))
    summary: dict[str, Any] = {
        "mean_n_nondominated": float(np.mean([r["n_nondominated"] for r in rows])),
        "n_seeds": len(seeds),
    }
    if hvs:
        summary["mean_hypervolume"] = float(np.mean(hvs))
        summary["std_hypervolume"] = float(np.std(hvs))
        summary["min_hypervolume"] = float(np.min(hvs))
    return {
        "algorithm": algorithm.algorithm.value,
        "seeds": seeds,
        "rows": rows,
        "summary": summary,
        "problem_fingerprint": problem_fingerprint(problem.model_dump(mode="json")),
        "message": "ok",
    }
