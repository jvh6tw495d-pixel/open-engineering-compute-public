"""Robust LP v0 — box uncertainty on constraint RHS. Merit: HiGHS."""

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


def robust_lp_box_rhs(
    base_ops: dict[str, Any],
    *,
    rhs_uncertainty: dict[str, float],
) -> dict[str, Any]:
    """Solve a robust LP under independent box uncertainty on selected RHS.

    For each named constraint in ``rhs_uncertainty`` with radius ``δ ≥ 0``:

    - sense ``<=``: worst-case tightens to ``rhs - δ``
    - sense ``>=``: worst-case tightens to ``rhs + δ``
    - sense ``=``: rejected in v0 (equality robustification needs two inequalities)

    Unmentioned constraints keep their nominal RHS.
    """
    if any(float(v) < 0 for v in rhs_uncertainty.values()):
        raise ValueError("rhs_uncertainty radii must be non-negative")

    ops = deepcopy(base_ops)
    if ops.get("problem_class") != "lp":
        raise ValueError("robust_lp_box_rhs requires problem_class='lp'")

    adjusted: dict[str, dict[str, float]] = {}
    constraints = list(ops.get("constraints") or [])
    for cons in constraints:
        name = str(cons.get("name"))
        if name not in rhs_uncertainty:
            continue
        delta = float(rhs_uncertainty[name])
        sense = str(cons.get("sense"))
        rhs = float(cons.get("rhs"))
        if sense == "<=":
            new_rhs = rhs - delta
        elif sense == ">=":
            new_rhs = rhs + delta
        else:
            raise ValueError(
                f"constraint {name!r} has sense '=' — robust equality not supported in v0"
            )
        cons["rhs"] = new_rhs
        adjusted[name] = {
            "delta": delta,
            "rhs_nominal": rhs,
            "rhs_robust": new_rhs,
            "sense_code": 1.0 if sense == ">=" else -1.0,
        }

    problem = validate_ops(ops)
    variables, linear_constraints, sense = ops_to_linear_parts(problem)
    issues = check_bound_conflicts(variables)
    if issues:
        return {
            "solver_status": "infeasible",
            "objective_value": None,
            "primal": {},
            "dual": {},
            "rhs_adjusted": adjusted,
            "feasibility_issues": issues,
            "backend": "precheck",
            "method": "box_rhs_worst_case",
            "converged": False,
        }

    try:
        solved = solve_linear(
            variables=variables,
            constraints=linear_constraints,
            sense=sense,  # type: ignore[arg-type]
            time_limit_seconds=problem.execution_limits.time_limit_seconds,
        )
    except HighsNotAvailableError as exc:
        return {
            "solver_status": "other",
            "objective_value": None,
            "primal": {},
            "dual": {},
            "rhs_adjusted": adjusted,
            "feasibility_issues": [exc.message],
            "backend": "highs",
            "method": "box_rhs_worst_case",
            "converged": False,
        }

    obj = solved.objective_value
    if obj is not None:
        obj = obj + float(problem.objective.offset)

    return {
        "solver_status": solved.status.value,
        "objective_value": obj,
        "primal": solved.primal,
        "dual": solved.dual,
        "rhs_adjusted": adjusted,
        "feasibility_issues": []
        if solved.status is SolverStatus.OPTIMAL
        else [f"HiGHS status: {solved.status.value}"],
        "backend": "highs",
        "method": "box_rhs_worst_case",
        "converged": solved.status is SolverStatus.OPTIMAL,
    }
