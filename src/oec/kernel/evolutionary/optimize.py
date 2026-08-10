"""Single-objective evolutionary optimization via pymoo (ADR 0031 + Part B depth)."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from oec.evolutionary.contracts import (
    AlgorithmName,
    EvolutionaryAlgorithmSpec,
    EvolutionaryProblemSpec,
)
from oec.evolutionary.hashing import problem_fingerprint
from oec.evolutionary.results import EvolutionaryResult
from oec.evolutionary.runtime import EvolutionaryRuntimeSpec, InequalityConstraintSpec
from oec.kernel.evolutionary.errors import PymooNotAvailableError
from oec.kernel.evolutionary.expression import evaluate_constraints, evaluate_expression
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


def _normalize_constraints(raw: list[Any]) -> list[InequalityConstraintSpec]:
    out: list[InequalityConstraintSpec] = []
    for i, c in enumerate(raw):
        if isinstance(c, InequalityConstraintSpec):
            out.append(c)
        elif isinstance(c, dict):
            out.append(InequalityConstraintSpec.model_validate(c))
        else:
            raise ValueError(f"constraint[{i}] must be InequalityConstraintSpec or dict")
    return out


def _objective_value(problem: EvolutionaryProblemSpec, x: np.ndarray) -> float:
    names = [v.name for v in problem.variables]
    if problem.expression is not None:
        return evaluate_expression(problem.expression, names, x)
    if problem.built_in is None:
        raise ValueError("problem has neither expression nor built_in")
    return evaluate_built_in(problem.built_in, x)


def optimize_single(
    problem: EvolutionaryProblemSpec,
    algorithm: EvolutionaryAlgorithmSpec,
    *,
    runtime: EvolutionaryRuntimeSpec | None = None,
) -> EvolutionaryResult:
    """Run a single-objective evolutionary search (built-in or expression IR)."""
    _pymoo_pkg, problem_cls, minimize = _require_pymoo()
    del _pymoo_pkg

    rt = runtime or EvolutionaryRuntimeSpec(seed=algorithm.seed, budget=algorithm.budget)
    budget = rt.budget or algorithm.budget
    seed = algorithm.seed if runtime is None else rt.seed

    n_var = len(problem.variables)
    xl = np.array([v.lower for v in problem.variables], dtype=float)
    xu = np.array([v.upper for v in problem.variables], dtype=float)
    sense = problem.sense
    names = [v.name for v in problem.variables]
    constraints = _normalize_constraints(list(problem.constraints or []))
    n_ieq = len(constraints)
    objective_mode = "expression" if problem.expression is not None else "built_in"

    class _BoxProblem(problem_cls):  # type: ignore[misc, valid-type]
        def __init__(self) -> None:
            super().__init__(n_var=n_var, n_obj=1, n_ieq_constr=n_ieq, xl=xl, xu=xu)

        def _evaluate(self, x: np.ndarray, out: dict[str, Any], *args: Any, **kwargs: Any) -> None:
            vals = np.empty(x.shape[0], dtype=float)
            if n_ieq:
                gmat = np.empty((x.shape[0], n_ieq), dtype=float)
            for i in range(x.shape[0]):
                f = _objective_value(problem, x[i])
                vals[i] = -f if sense == "max" else f
                if n_ieq:
                    gmat[i] = evaluate_constraints(constraints, names, x[i])
            out["F"] = vals.reshape(-1, 1)
            if n_ieq:
                out["G"] = gmat

    algo = _make_algorithm(algorithm.algorithm, budget.population)
    termination_gens = budget.generations

    termination: Any = ("n_gen", termination_gens)
    if rt.max_evaluations is not None or rt.max_seconds is not None:
        try:
            from pymoo.termination.collection import TerminationCollection
            from pymoo.termination.max_eval import MaximumFunctionCallTermination
            from pymoo.termination.max_gen import MaximumGenerationTermination
            from pymoo.termination.max_time import TimeBasedTermination

            terms: list[Any] = [MaximumGenerationTermination(termination_gens)]
            if rt.max_evaluations is not None:
                terms.append(MaximumFunctionCallTermination(rt.max_evaluations))
            if rt.max_seconds is not None:
                terms.append(TimeBasedTermination(rt.max_seconds))
            termination = TerminationCollection(*terms)
        except ImportError:
            termination = ("n_gen", termination_gens)

    history_best: list[float] = []
    t0 = time.perf_counter()
    res = minimize(
        _BoxProblem(),
        algo,
        termination=termination,
        seed=seed,
        verbose=False,
        save_history=bool(rt.history),
    )
    elapsed = time.perf_counter() - t0

    if res.history:
        for gen in res.history:
            fitness = gen.pop.get("F")
            if fitness is not None and len(fitness):
                history_best.append(float(np.min(fitness)))

    if res.X is None or res.F is None:
        raise RuntimeError("pymoo returned no solution")

    x_best = np.asarray(res.X, dtype=float).reshape(-1)
    f_min_space = float(np.asarray(res.F).reshape(-1)[0])
    f_report = -f_min_space if sense == "max" else f_min_space
    history_report = [-h if sense == "max" else h for h in history_best]

    n_eval = int(res.algorithm.evaluator.n_eval) if hasattr(res.algorithm, "evaluator") else 0
    best_x = {problem.variables[i].name: float(x_best[i]) for i in range(n_var)}

    # Feasibility of best point
    feas = 1.0
    if n_ieq:
        g_best = evaluate_constraints(constraints, names, x_best)
        feas = 1.0 if all(g <= 1e-9 for g in g_best) else 0.0

    return EvolutionaryResult(
        backend="pymoo",
        backend_version=_pymoo_version(),
        algorithm=algorithm.algorithm.value,
        seed=seed,
        deterministic_status="practical",
        sense=sense,
        best_objective=f_report,
        best_x=best_x,
        n_evaluations=n_eval,
        n_generations=len(history_best) if history_best else termination_gens,
        history_best=history_report if rt.history else [],
        problem_fingerprint=problem_fingerprint(problem.model_dump(mode="json")),
        feasibility_rate=feas,
        message="ok",
        n_constraints=n_ieq,
        objective_mode=objective_mode,
        runtime={
            "max_seconds": rt.max_seconds,
            "max_evaluations": rt.max_evaluations,
            "elapsed_seconds": elapsed,
            "budget_generations": budget.generations,
            "budget_population": budget.population,
        },
    )
