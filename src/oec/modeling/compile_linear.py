"""Compile a Math IR ``linear_program`` document to OPS and solve via HiGHS.

Thin adapter — no new solver logic. The compiled call sequence is
byte-for-byte the same as ``optimization.lp``'s ``implementation.py``
(``ops_to_linear_parts`` -> ``check_bound_conflicts`` -> ``solve_linear``),
which is what makes the two paths' outputs directly comparable for the v2.2
parity gate.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.optimization.highs import (
    HighsNotAvailableError,
    SolverStatus,
    check_bound_conflicts,
    solve_linear,
)
from oec.modeling.ir import MathProblem
from oec.ops.convert import ops_to_linear_parts
from oec.ops.models import OPSProblem, OPSVariable


def to_ops_problem(problem: MathProblem) -> OPSProblem:
    """Translate the linear_program variant of ``problem`` into an OPSProblem."""
    if problem.objective is None:
        raise ValueError("MathProblem has no objective; it is not a linear_program")

    variables = [
        OPSVariable(name=symbol.name, lower=symbol.lower, upper=symbol.upper)
        for symbol in problem.symbols
    ]
    return OPSProblem(
        problem_class="lp",
        sense=problem.sense,
        assumptions=list(problem.assumptions),
        notes=problem.notes or None,
        variables=variables,
        constraints=list(problem.constraints),
        objective=problem.objective,
    )


def compile_linear(problem: MathProblem) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile and solve ``problem``, returning ``(result, diagnostics)``.

    The output shape matches ``optimization.lp``'s own ``execute`` return
    value exactly, so the two paths can be compared field-by-field.
    """
    ops_problem = to_ops_problem(problem)
    variables, constraints, sense = ops_to_linear_parts(ops_problem)

    bound_issues = check_bound_conflicts(variables)
    if bound_issues:
        return (
            {
                "solver_status": "infeasible",
                "objective_value": None,
                "primal": {},
                "dual": {},
                "feasibility_issues": bound_issues,
                "backend": "highs",
            },
            {"converged": False, "message": "bound conflicts detected before solve"},
        )

    time_limit = ops_problem.execution_limits.time_limit_seconds
    try:
        solved = solve_linear(
            variables=variables,
            constraints=constraints,
            sense=sense,  # type: ignore[arg-type]
            time_limit_seconds=time_limit,
        )
    except HighsNotAvailableError as exc:
        return (
            {
                "solver_status": "other",
                "objective_value": None,
                "primal": {},
                "dual": {},
                "feasibility_issues": [exc.message],
                "backend": "highs",
            },
            {"converged": False, "message": exc.message},
        )

    issues: list[str] = []
    if solved.status is SolverStatus.INFEASIBLE:
        issues.append("HiGHS reported the LP as infeasible")
    elif solved.status is SolverStatus.UNBOUNDED:
        issues.append("HiGHS reported the LP as unbounded")

    converged = solved.status is SolverStatus.OPTIMAL
    objective_value = solved.objective_value
    if objective_value is not None:
        objective_value = objective_value + float(ops_problem.objective.offset)

    return (
        {
            "solver_status": solved.status.value,
            "objective_value": objective_value,
            "primal": solved.primal,
            "dual": solved.dual,
            "feasibility_issues": issues,
            "backend": "highs",
        },
        {
            "converged": converged,
            "message": solved.message,
            "raw_status": solved.raw_status,
        },
    )
