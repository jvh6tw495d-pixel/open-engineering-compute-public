"""Bi-objective LP Pareto approximation v0. Merit: HiGHS via weighted sum."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from oec.kernel.optimization.highs import (
    HighsNotAvailableError,
    SolverStatus,
    check_bound_conflicts,
    solve_linear,
)
from oec.ops.convert import ops_to_linear_parts
from oec.ops.models import validate_ops


def _solve_combined(
    base_ops: dict[str, Any],
    combined: dict[str, float],
) -> dict[str, Any]:
    ops = deepcopy(base_ops)
    ops["objective"] = {"coeffs": combined, "offset": 0.0}
    problem = validate_ops(ops)
    variables, constraints, sense = ops_to_linear_parts(problem)
    issues = check_bound_conflicts(variables)
    if issues:
        return {
            "solver_status": "infeasible",
            "primal": {},
            "feasibility_issues": issues,
            "backend": "precheck",
        }
    try:
        solved = solve_linear(
            variables=variables,
            constraints=constraints,
            sense=sense,  # type: ignore[arg-type]
            time_limit_seconds=problem.execution_limits.time_limit_seconds,
        )
    except HighsNotAvailableError as exc:
        return {
            "solver_status": "other",
            "primal": {},
            "feasibility_issues": [exc.message],
            "backend": "highs",
        }
    return {
        "solver_status": solved.status.value,
        "primal": solved.primal,
        "feasibility_issues": [],
        "backend": "highs",
        "raw_status": solved.raw_status,
        "converged": solved.status is SolverStatus.OPTIMAL,
    }


def _obj_value(coeffs: dict[str, float], primal: dict[str, float]) -> float:
    return float(
        sum(
            float(coeffs.get(n, 0.0)) * float(primal.get(n, 0.0)) for n in set(coeffs) | set(primal)
        )
    )


def pareto_weighted_sum(
    base_ops: dict[str, Any],
    *,
    objective_a: dict[str, float],
    objective_b: dict[str, float],
    n_points: int = 11,
) -> dict[str, Any]:
    """Approximate a bi-objective Pareto set by sweeping convex weights.

    For ``w`` on a uniform grid in ``[0, 1]``:
    ``combined = w * c_a + (1-w) * c_b``. Returns points with both objective
    values and keeps a simple non-dominated filter (minimization sense of
    both objectives; if base sense is max, values are reported as-is and
    dominance uses the base sense).
    """
    if n_points < 2:
        raise ValueError("n_points must be >= 2")
    if not objective_a or not objective_b:
        raise ValueError("objective_a and objective_b must be non-empty")

    sense = str(base_ops.get("sense", "min")).lower()
    points: list[dict[str, Any]] = []
    for i in range(n_points):
        w = i / (n_points - 1)
        combined: dict[str, float] = {}
        for name, coeff in objective_a.items():
            combined[name] = combined.get(name, 0.0) + w * float(coeff)
        for name, coeff in objective_b.items():
            combined[name] = combined.get(name, 0.0) + (1.0 - w) * float(coeff)
        solved = _solve_combined(base_ops, combined)
        if solved.get("solver_status") != "optimal" or not solved.get("primal"):
            points.append(
                {
                    "weight_a": w,
                    "weight_b": 1.0 - w,
                    "solver_status": solved.get("solver_status"),
                    "objective_a": None,
                    "objective_b": None,
                    "primal": {},
                    "feasibility_issues": solved.get("feasibility_issues", []),
                }
            )
            continue
        primal = solved["primal"]
        points.append(
            {
                "weight_a": w,
                "weight_b": 1.0 - w,
                "solver_status": "optimal",
                "objective_a": _obj_value(objective_a, primal),
                "objective_b": _obj_value(objective_b, primal),
                "primal": primal,
                "feasibility_issues": [],
            }
        )

    # Non-dominated filter among successful points.
    successful = [
        p for p in points if p["objective_a"] is not None and p["objective_b"] is not None
    ]
    nondominated: list[dict[str, Any]] = []
    for p in successful:
        dominated = False
        for q in successful:
            if q is p:
                continue
            if sense == "max":
                better_or_eq = (
                    q["objective_a"] >= p["objective_a"] and q["objective_b"] >= p["objective_b"]
                )
                strictly = (
                    q["objective_a"] > p["objective_a"] or q["objective_b"] > p["objective_b"]
                )
            else:
                better_or_eq = (
                    q["objective_a"] <= p["objective_a"] and q["objective_b"] <= p["objective_b"]
                )
                strictly = (
                    q["objective_a"] < p["objective_a"] or q["objective_b"] < p["objective_b"]
                )
            if better_or_eq and strictly:
                dominated = True
                break
        if not dominated:
            nondominated.append(p)

    return {
        "n_points_requested": int(n_points),
        "n_solved_optimal": sum(1 for p in points if p["solver_status"] == "optimal"),
        "n_nondominated": len(nondominated),
        "points": points,
        "nondominated": nondominated,
        "sense": sense,
        "method": "weighted_sum_sweep",
        "backend": "highs",
        "converged": None,
    }
