"""Single-objective evolutionary optimization via pymoo (ADR 0031)."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.evolutionary.contracts import (
    AlgorithmName,
    EvolutionaryAlgorithmSpec,
    EvolutionaryProblemSpec,
)
from oec.evolutionary.hashing import problem_fingerprint
from oec.evolutionary.results import EvolutionaryResult
from oec.kernel.evolutionary.errors import PymooNotAvailableError
from oec.kernel.evolutionary.problems import evaluate_built_in


def _require_pymoo() -> tuple[Any, Any, Any]:
    try:
        import pymoo
        from pymoo.core.problem import Problem
        from pymoo.optimize import minimize
    except ImportError as exc:
        raise PymooNotAvailableError(
            "pymoo is not installed. Install with: uv sync --extra evolutionary"
        ) from exc
    return pymoo, Problem, minimize


def _pymoo_version() -> str | None:
    try:
        import importlib.metadata

        return importlib.metadata.version("pymoo")
    except Exception:  # noqa: BLE001
        return None


def _make_algorithm(name: AlgorithmName, pop_size: int) -> Any:
    if name == AlgorithmName.DIFFERENTIAL_EVOLUTION:
        from pymoo.algorithms.soo.nonconvex.de import DE

        return DE(pop_size=pop_size)
    if name == AlgorithmName.GENETIC_ALGORITHM:
        from pymoo.algorithms.soo.nonconvex.ga import GA

        return GA(pop_size=pop_size)
    if name == AlgorithmName.CMA_ES:
        from pymoo.algorithms.soo.nonconvex.cmaes import CMAES

        return CMAES()
    if name == AlgorithmName.PSO:
        from pymoo.algorithms.soo.nonconvex.pso import PSO

        return PSO(pop_size=pop_size)
    raise ValueError(f"unsupported algorithm {name}")


def optimize_single(
    problem: EvolutionaryProblemSpec,
    algorithm: EvolutionaryAlgorithmSpec,
) -> EvolutionaryResult:
    """Run a single-objective evolutionary search on a built-in problem."""
    _pymoo_pkg, problem_cls, minimize = _require_pymoo()
    del _pymoo_pkg

    n_var = len(problem.variables)
    xl = np.array([v.lower for v in problem.variables], dtype=float)
    xu = np.array([v.upper for v in problem.variables], dtype=float)
    built_in = problem.built_in
    sense = problem.sense

    class _BoxProblem(problem_cls):  # type: ignore[misc, valid-type]
        def __init__(self) -> None:
            super().__init__(n_var=n_var, n_obj=1, n_ieq_constr=0, xl=xl, xu=xu)

        def _evaluate(self, x: np.ndarray, out: dict[str, Any], *args: Any, **kwargs: Any) -> None:
            vals = np.empty(x.shape[0], dtype=float)
            for i in range(x.shape[0]):
                f = evaluate_built_in(built_in, x[i])
                vals[i] = -f if sense == "max" else f
            out["F"] = vals.reshape(-1, 1)

    algo = _make_algorithm(algorithm.algorithm, algorithm.budget.population)
    termination_gens = algorithm.budget.generations

    # History of best-so-far (minimize space)
    history_best: list[float] = []

    res = minimize(
        _BoxProblem(),
        algo,
        termination=("n_gen", termination_gens),
        seed=algorithm.seed,
        verbose=False,
        save_history=True,
    )

    if res.history:
        for gen in res.history:
            fitness = gen.pop.get("F")
            if fitness is not None and len(fitness):
                history_best.append(float(np.min(fitness)))

    # Best solution
    if res.X is None or res.F is None:
        raise RuntimeError("pymoo returned no solution")

    x_best = np.asarray(res.X, dtype=float).reshape(-1)
    f_min_space = float(np.asarray(res.F).reshape(-1)[0])
    f_report = -f_min_space if sense == "max" else f_min_space

    # Prefer true objective history in report sense
    history_report = [-h if sense == "max" else h for h in history_best]

    n_eval = int(res.algorithm.evaluator.n_eval) if hasattr(res.algorithm, "evaluator") else 0
    best_x = {problem.variables[i].name: float(x_best[i]) for i in range(n_var)}

    return EvolutionaryResult(
        backend="pymoo",
        backend_version=_pymoo_version(),
        algorithm=algorithm.algorithm.value,
        seed=algorithm.seed,
        deterministic_status="practical",
        sense=sense,
        best_objective=f_report,
        best_x=best_x,
        n_evaluations=n_eval,
        n_generations=len(history_best) if history_best else termination_gens,
        history_best=history_report,
        problem_fingerprint=problem_fingerprint(problem.model_dump(mode="json")),
        feasibility_rate=1.0,
        message="ok",
    )
