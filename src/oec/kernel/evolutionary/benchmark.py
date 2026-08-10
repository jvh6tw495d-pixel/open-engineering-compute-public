"""X1 thin evolutionary benchmark harness (controlled multi-run table)."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.evolutionary.contracts import (
    BenchmarkSpec,
    BudgetSpec,
    EvolutionaryAlgorithmSpec,
    EvolutionaryProblemSpec,
    MultiObjectiveAlgorithmSpec,
    MultiObjectiveProblemSpec,
)
from oec.evolutionary.hashing import problem_fingerprint
from oec.evolutionary.results import BenchmarkResult
from oec.kernel.evolutionary.multiobjective import optimize_multi
from oec.kernel.evolutionary.optimize import optimize_single


def run_benchmark(spec: BenchmarkSpec) -> BenchmarkResult:
    """Run the same problem across algorithms × seeds; return a comparison table."""
    if spec.mode == "single":
        return _run_single(spec)
    return _run_multi(spec)


def _run_single(spec: BenchmarkSpec) -> BenchmarkResult:
    assert spec.built_in is not None
    rows: list[dict[str, Any]] = []
    problem = EvolutionaryProblemSpec(
        variables=list(spec.variables),
        sense="min",
        built_in=spec.built_in,
    )
    fp = problem_fingerprint(problem.model_dump(mode="json"))
    algos = [a.value for a in spec.algorithms]
    for algo in spec.algorithms:
        for seed in spec.seeds:
            result = optimize_single(
                problem,
                EvolutionaryAlgorithmSpec(
                    algorithm=algo,
                    budget=BudgetSpec(
                        generations=spec.generations,
                        population=spec.population,
                    ),
                    seed=seed,
                ),
            )
            rows.append(
                {
                    "algorithm": algo.value,
                    "seed": seed,
                    "best_objective": result.best_objective,
                    "n_evaluations": result.n_evaluations,
                    "n_generations": result.n_generations,
                }
            )
    return BenchmarkResult(
        mode="single",
        problem_fingerprint=fp,
        seeds=list(spec.seeds),
        algorithms=algos,
        rows=rows,
        summary=_summarize_single(rows, algos),
        message="ok",
    )


def _run_multi(spec: BenchmarkSpec) -> BenchmarkResult:
    assert spec.multi_built_in is not None
    rows: list[dict[str, Any]] = []
    problem_m = MultiObjectiveProblemSpec(
        variables=list(spec.variables),
        built_in=spec.multi_built_in,
        n_objectives=2,
    )
    fp = problem_fingerprint(problem_m.model_dump(mode="json"))
    algos = [a.value for a in spec.multi_algorithms]
    for algo in spec.multi_algorithms:
        for seed in spec.seeds:
            result = optimize_multi(
                problem_m,
                MultiObjectiveAlgorithmSpec(
                    algorithm=algo,
                    budget=BudgetSpec(
                        generations=spec.generations,
                        population=spec.population,
                    ),
                    seed=seed,
                ),
            )
            rows.append(
                {
                    "algorithm": algo.value,
                    "seed": seed,
                    "n_nondominated": result.n_nondominated,
                    "hypervolume": result.hypervolume,
                    "n_evaluations": result.n_evaluations,
                }
            )
    return BenchmarkResult(
        mode="multi",
        problem_fingerprint=fp,
        seeds=list(spec.seeds),
        algorithms=algos,
        rows=rows,
        summary=_summarize_multi(rows, algos),
        message="ok",
    )


def _summarize_single(rows: list[dict[str, Any]], algorithms: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for algo in algorithms:
        vals = [r["best_objective"] for r in rows if r["algorithm"] == algo]
        if not vals:
            continue
        arr = np.asarray(vals, dtype=float)
        out[algo] = {
            "mean_best_objective": float(np.mean(arr)),
            "std_best_objective": float(np.std(arr)),
            "min_best_objective": float(np.min(arr)),
            "n_seeds": len(vals),
        }
    # best mean (min)
    if out:
        best_algo = min(out.keys(), key=lambda a: out[a]["mean_best_objective"])
        out["best_mean_algorithm"] = best_algo
        out["note"] = (
            "best_mean_algorithm is lowest mean best_objective under the shared "
            "budget/seeds; not a universal claim of superiority (X1)."
        )
    return out


def _summarize_multi(rows: list[dict[str, Any]], algorithms: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for algo in algorithms:
        hvs = [
            r["hypervolume"]
            for r in rows
            if r["algorithm"] == algo and r["hypervolume"] is not None
        ]
        nds = [r["n_nondominated"] for r in rows if r["algorithm"] == algo]
        if not nds:
            continue
        entry: dict[str, Any] = {
            "mean_n_nondominated": float(np.mean(nds)),
            "n_seeds": len(nds),
        }
        if hvs:
            entry["mean_hypervolume"] = float(np.mean(hvs))
            entry["std_hypervolume"] = float(np.std(hvs))
        out[algo] = entry
    if out:
        # prefer HV if present
        def _score(a: str) -> float:
            e = out[a]
            if "mean_hypervolume" in e:
                return float(e["mean_hypervolume"])
            return float(e["mean_n_nondominated"])

        best_algo = max(out.keys(), key=_score)
        out["best_mean_algorithm"] = best_algo
        out["note"] = (
            "Ranking uses mean hypervolume when available else mean n_nondominated; "
            "shared budget/seeds only — not a universal claim (X1)."
        )
    return out
