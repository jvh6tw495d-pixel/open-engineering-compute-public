"""Multiobjective scalarization v0 (S25–S26). Weighted sum → single LP via HiGHS."""

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


def weighted_sum_lp(
    base_ops: dict[str, Any],
    *,
    objectives: list[dict[str, float]],
    weights: list[float],
) -> dict[str, Any]:
    """Solve min/max Σ w_k * (c_k · x) with shared constraints from base OPS.

    ``objectives`` is a list of coeff maps; ``weights`` same length.
    Sense comes from ``base_ops.sense``.
    """
    if not objectives or len(objectives) != len(weights):
        raise ValueError("objectives and weights must be non-empty and same length")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    wsum = float(sum(weights))
    if wsum <= 0:
        raise ValueError("at least one weight must be positive")
    norm_w = [float(w) / wsum for w in weights]

    ops = deepcopy(base_ops)
    combined: dict[str, float] = {}
    for w, coeffs in zip(norm_w, objectives, strict=True):
        for name, coeff in coeffs.items():
            combined[name] = combined.get(name, 0.0) + w * float(coeff)
    ops["objective"] = {"coeffs": combined, "offset": 0.0}

    problem = validate_ops(ops)
    variables, constraints, sense = ops_to_linear_parts(problem)
    issues = check_bound_conflicts(variables)
    if issues:
        return {
            "solver_status": "infeasible",
            "objective_value": None,
            "primal": {},
            "weights_normalized": norm_w,
            "combined_coeffs": combined,
            "feasibility_issues": issues,
            "backend": "precheck",
            "method": "weighted_sum",
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
            "objective_value": None,
            "primal": {},
            "weights_normalized": norm_w,
            "combined_coeffs": combined,
            "feasibility_issues": [exc.message],
            "backend": "highs",
            "method": "weighted_sum",
        }

    # Per-objective values at solution
    per_obj: list[float | None] = []
    if solved.primal:
        for coeffs in objectives:
            total = 0.0
            for n, xv in solved.primal.items():
                total += float(coeffs.get(n, 0.0)) * float(xv)
            per_obj.append(total)
    else:
        per_obj = [None] * len(objectives)

    return {
        "solver_status": solved.status.value,
        "objective_value": solved.objective_value,
        "primal": solved.primal,
        "weights_normalized": norm_w,
        "combined_coeffs": combined,
        "objective_values": per_obj,
        "feasibility_issues": []
        if solved.status is SolverStatus.OPTIMAL
        else [solved.status.value],
        "backend": "highs",
        "method": "weighted_sum",
        "success": solved.status is SolverStatus.OPTIMAL,
    }
