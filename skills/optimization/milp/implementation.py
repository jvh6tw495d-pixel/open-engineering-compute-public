"""optimization.milp — MILP via HiGHS."""

from __future__ import annotations

from typing import Any

from oec.kernel.optimization.highs import (
    HighsNotAvailableError,
    SolverStatus,
    check_bound_conflicts,
    solve_linear,
)
from oec.ops.convert import ops_to_linear_parts
from oec.ops.models import validate_ops


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    problem = validate_ops(inputs["ops"])
    if problem.problem_class != "milp":
        raise ValueError("optimization.milp requires ops.problem_class='milp'")

    variables, constraints, sense = ops_to_linear_parts(problem)
    bound_issues = check_bound_conflicts(variables)
    if bound_issues:
        return {
            "result": {
                "solver_status": "infeasible",
                "objective_value": None,
                "primal": {},
                "mip_gap": None,
                "mip_node_count": None,
                "feasibility_issues": bound_issues,
                "backend": "highs",
            },
            "diagnostics": {
                "converged": False,
                "message": "bound conflicts detected before solve",
            },
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
            "result": {
                "solver_status": "other",
                "objective_value": None,
                "primal": {},
                "mip_gap": None,
                "mip_node_count": None,
                "feasibility_issues": [exc.message],
                "backend": "highs",
            },
            "diagnostics": {"converged": False, "message": exc.message},
        }

    issues: list[str] = []
    if solved.status is SolverStatus.INFEASIBLE:
        issues.append("HiGHS reported the MILP as infeasible")
    elif solved.status is SolverStatus.UNBOUNDED:
        issues.append("HiGHS reported the MILP as unbounded")
    elif solved.status is SolverStatus.TIME_LIMIT:
        issues.append("HiGHS stopped on time limit (incumbent may be partial)")

    converged = solved.status is SolverStatus.OPTIMAL
    obj = solved.objective_value
    if obj is not None:
        obj = obj + float(problem.objective.offset)

    return {
        "result": {
            "solver_status": solved.status.value,
            "objective_value": obj,
            "primal": solved.primal,
            "mip_gap": solved.mip_gap,
            "mip_node_count": solved.mip_node_count,
            "feasibility_issues": issues,
            "backend": "highs",
        },
        "diagnostics": {
            "converged": converged,
            "message": solved.message,
            "raw_status": solved.raw_status,
        },
    }
