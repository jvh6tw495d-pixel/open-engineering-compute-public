"""Multi-objective evolutionary search via pymoo (E2, ADR 0031)."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.evolutionary.contracts import (
    MultiObjectiveAlgorithmName,
    MultiObjectiveAlgorithmSpec,
    MultiObjectiveProblemSpec,
)
from oec.evolutionary.hashing import problem_fingerprint
from oec.evolutionary.results import EvolutionaryParetoResult
from oec.kernel.evolutionary.errors import PymooNotAvailableError
from oec.kernel.evolutionary.multi_problems import evaluate_multi


def _require_pymoo() -> tuple[Any, Any]:
    try:
        from pymoo.core.problem import Problem
        from pymoo.optimize import minimize
    except ImportError as exc:
        raise PymooNotAvailableError(
            "pymoo is not installed. Install with: uv sync --extra evolutionary"
        ) from exc
    return Problem, minimize


def _pymoo_version() -> str | None:
    try:
        import importlib.metadata

        return importlib.metadata.version("pymoo")
    except Exception:  # noqa: BLE001
        return None


def _make_mo_algorithm(name: MultiObjectiveAlgorithmName, pop_size: int, n_partitions: int) -> Any:
    if name == MultiObjectiveAlgorithmName.NSGA2:
        from pymoo.algorithms.moo.nsga2 import NSGA2

        return NSGA2(pop_size=pop_size)
    if name == MultiObjectiveAlgorithmName.NSGA3:
        from pymoo.algorithms.moo.nsga3 import NSGA3
        from pymoo.util.ref_dirs import get_reference_directions

        ref_dirs = get_reference_directions("das-dennis", 2, n_partitions=n_partitions)
        return NSGA3(pop_size=pop_size, ref_dirs=ref_dirs)
    if name == MultiObjectiveAlgorithmName.MOEAD:
        from pymoo.algorithms.moo.moead import MOEAD
        from pymoo.util.ref_dirs import get_reference_directions

        ref_dirs = get_reference_directions("das-dennis", 2, n_partitions=n_partitions)
        return MOEAD(ref_dirs=ref_dirs, n_neighbors=min(15, len(ref_dirs)))
    raise ValueError(f"unsupported multi-objective algorithm {name}")


def _hypervolume_2d(points: np.ndarray, ref: np.ndarray) -> float | None:
    """Simple 2D hypervolume for minimization (no external HV lib required)."""
    if points.size == 0 or points.shape[1] != 2:
        return None
    # Filter dominated / outside ref
    pts = points[np.all(points <= ref, axis=1)]
    if pts.size == 0:
        return 0.0
    # Sort by f1 ascending
    order = np.argsort(pts[:, 0])
    pts = pts[order]
    hv = 0.0
    prev_f2 = ref[1]
    for i in range(len(pts) - 1, -1, -1):
        f1, f2 = float(pts[i, 0]), float(pts[i, 1])
        if f2 >= prev_f2:
            continue
        width = ref[0] - f1
        if width <= 0:
            continue
        hv += width * (prev_f2 - f2)
        prev_f2 = f2
    return float(max(hv, 0.0))


def optimize_multi(
    problem: MultiObjectiveProblemSpec,
    algorithm: MultiObjectiveAlgorithmSpec,
    *,
    runtime: Any | None = None,
) -> EvolutionaryParetoResult:
    """Run multi-objective search; return non-dominated set.

    Optional ``runtime.hv_reference`` fixes the hypervolume reference point
    (Part B E-D4) instead of auto-scaling from the front.
    """
    problem_cls, minimize = _require_pymoo()

    n_var = len(problem.variables)
    xl = np.array([v.lower for v in problem.variables], dtype=float)
    xu = np.array([v.upper for v in problem.variables], dtype=float)
    built_in = problem.built_in
    n_obj = problem.n_objectives
    seed = algorithm.seed
    budget = algorithm.budget
    hv_ref_list: list[float] | None = None
    if runtime is not None:
        seed = getattr(runtime, "seed", seed)
        if getattr(runtime, "budget", None) is not None:
            budget = runtime.budget
        hv_ref_list = getattr(runtime, "hv_reference", None)

    class _BoxMOProblem(problem_cls):  # type: ignore[misc, valid-type]
        def __init__(self) -> None:
            super().__init__(n_var=n_var, n_obj=n_obj, n_ieq_constr=0, xl=xl, xu=xu)

        def _evaluate(self, x: np.ndarray, out: dict[str, Any], *args: Any, **kwargs: Any) -> None:
            f = np.empty((x.shape[0], n_obj), dtype=float)
            for i in range(x.shape[0]):
                f[i] = evaluate_multi(built_in, x[i])
            out["F"] = f

    algo = _make_mo_algorithm(
        algorithm.algorithm,
        budget.population,
        algorithm.n_partitions,
    )
    res = minimize(
        _BoxMOProblem(),
        algo,
        termination=("n_gen", budget.generations),
        seed=seed,
        verbose=False,
        save_history=False,
    )

    if res.X is None or res.F is None:
        raise RuntimeError("pymoo returned no multi-objective solution")

    x_mat = np.atleast_2d(np.asarray(res.X, dtype=float))
    f_mat = np.atleast_2d(np.asarray(res.F, dtype=float))
    if x_mat.shape[0] != f_mat.shape[0]:
        x_mat = x_mat.reshape(1, -1)
        f_mat = f_mat.reshape(1, -1)

    nd_mask = _nondominated_mask(f_mat)
    decision_vectors: list[dict[str, float]] = []
    objective_vectors: list[list[float]] = []
    mask_list: list[bool] = []
    for i in range(x_mat.shape[0]):
        decision_vectors.append(
            {problem.variables[j].name: float(x_mat[i, j]) for j in range(n_var)}
        )
        objective_vectors.append([float(v) for v in f_mat[i]])
        mask_list.append(bool(nd_mask[i]))

    nd_f = f_mat[nd_mask]
    if hv_ref_list is not None and len(hv_ref_list) >= n_obj:
        ref = np.asarray(hv_ref_list[:n_obj], dtype=float)
    else:
        ref = np.max(f_mat, axis=0) + 0.1 * (np.ptp(f_mat, axis=0) + 1e-9)
    hv = _hypervolume_2d(nd_f, ref) if n_obj == 2 else None

    n_eval = int(res.algorithm.evaluator.n_eval) if hasattr(res.algorithm, "evaluator") else 0

    return EvolutionaryParetoResult(
        backend="pymoo",
        backend_version=_pymoo_version(),
        algorithm=algorithm.algorithm.value,
        seed=seed,
        deterministic_status="practical",
        n_objectives=n_obj,
        decision_vectors=decision_vectors,
        objective_vectors=objective_vectors,
        nondominated_mask=mask_list,
        n_nondominated=int(np.sum(nd_mask)),
        n_evaluations=n_eval,
        n_generations=budget.generations,
        hypervolume=hv,
        hv_reference=ref.tolist() if n_obj == 2 else None,
        problem_fingerprint=problem_fingerprint(problem.model_dump(mode="json")),
        message="ok",
        runtime={
            "hv_reference_mode": "fixed" if hv_ref_list is not None else "auto",
        },
    )


def _nondominated_mask(fitness: np.ndarray) -> np.ndarray:
    """Boolean mask of non-dominated rows (minimization)."""
    n = fitness.shape[0]
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        if not mask[i]:
            continue
        for j in range(n):
            if i == j or not mask[j]:
                continue
            # j dominates i if all <= and one <
            if np.all(fitness[j] <= fitness[i]) and np.any(fitness[j] < fitness[i]):
                mask[i] = False
                break
    return mask
