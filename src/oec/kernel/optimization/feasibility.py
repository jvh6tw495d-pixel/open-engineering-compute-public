"""Feasibility diagnostics for linear OPS (S7′). Backend merit: HiGHS."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from oec.kernel.optimization.highs import (
    HighsNotAvailableError,
    LinearVariable,
    SolverStatus,
    check_bound_conflicts,
    solve_linear,
)
from oec.ops.convert import ops_to_linear_parts
from oec.ops.models import validate_ops


def check_feasibility(ops_document: dict[str, Any]) -> dict[str, Any]:
    """Check LP/MILP feasibility without claiming an optimal business objective.

    Uses zero objective (feasibility-only solve) after bound pre-checks.
    """
    problem = validate_ops(ops_document)
    variables, constraints, sense = ops_to_linear_parts(problem)

    issues: list[str] = list(check_bound_conflicts(variables))
    # Obvious empty-coeff already rejected by OPS validation.
    empty_like = [c.name for c in constraints if not c.coeffs]
    for name in empty_like:
        issues.append(f"constraint {name!r} has no coefficients")

    if issues:
        return {
            "feasible": False,
            "solver_status": "infeasible",
            "feasibility_issues": issues,
            "primal": {},
            "backend": "precheck",
            "problem_class": problem.problem_class,
            "sense": sense,
        }

    # Zero out objective for pure feasibility.
    zero_vars = [
        LinearVariable(
            name=v.name,
            lower=v.lower,
            upper=v.upper,
            kind=v.kind,
            objective_coeff=0.0,
        )
        for v in variables
    ]
    time_limit = problem.execution_limits.time_limit_seconds
    try:
        solved = solve_linear(
            variables=zero_vars,
            constraints=constraints,
            sense="min",
            time_limit_seconds=time_limit,
        )
    except HighsNotAvailableError as exc:
        return {
            "feasible": False,
            "solver_status": "other",
            "feasibility_issues": [exc.message],
            "primal": {},
            "backend": "highs",
            "problem_class": problem.problem_class,
            "sense": sense,
        }

    feasible = solved.status is SolverStatus.OPTIMAL
    msg_issues: list[str] = list(issues)
    if solved.status is SolverStatus.INFEASIBLE:
        msg_issues.append("HiGHS reported the problem as infeasible")
    elif solved.status is SolverStatus.UNBOUNDED:
        # Feasibility-only with zero obj shouldn't be unbounded unless free vars;
        # still report it.
        msg_issues.append("HiGHS reported the problem as unbounded under zero objective")
    elif not feasible:
        msg_issues.append(f"HiGHS status: {solved.status.value} ({solved.message})")

    return {
        "feasible": feasible,
        "solver_status": solved.status.value,
        "feasibility_issues": msg_issues,
        "primal": solved.primal if feasible else {},
        "backend": "highs",
        "problem_class": problem.problem_class,
        "sense": sense,
        "raw_status": solved.raw_status,
    }


def scenario_batch(
    base_ops: dict[str, Any],
    *,
    path: str,
    values: list[float],
) -> dict[str, Any]:
    """Sweep a numeric field in OPS and re-solve each scenario (S7′ v0).

    ``path`` forms supported:
    - ``constraint:<name>.rhs``
    - ``objective.coeffs.<var>``
    - ``variable:<name>.lower`` / ``variable:<name>.upper``
    """
    if not values:
        raise ValueError("values must be non-empty")
    if len(values) > 50:
        raise ValueError("scenario_batch v0 allows at most 50 scenarios")

    results: list[dict[str, Any]] = []
    for i, value in enumerate(values):
        ops = deepcopy(base_ops)
        _apply_path(ops, path, float(value))
        problem = validate_ops(ops)
        variables, constraints, sense = ops_to_linear_parts(problem)
        bound_issues = check_bound_conflicts(variables)
        if bound_issues:
            results.append(
                {
                    "index": i,
                    "path": path,
                    "value": float(value),
                    "solver_status": "infeasible",
                    "objective_value": None,
                    "primal": {},
                    "feasibility_issues": bound_issues,
                }
            )
            continue
        try:
            solved = solve_linear(
                variables=variables,
                constraints=constraints,
                sense=sense,  # type: ignore[arg-type]
                time_limit_seconds=problem.execution_limits.time_limit_seconds,
            )
        except HighsNotAvailableError as exc:
            results.append(
                {
                    "index": i,
                    "path": path,
                    "value": float(value),
                    "solver_status": "other",
                    "objective_value": None,
                    "primal": {},
                    "feasibility_issues": [exc.message],
                }
            )
            continue
        obj = solved.objective_value
        if obj is not None:
            obj = obj + float(problem.objective.offset)
        issues: list[str] = []
        if solved.status is SolverStatus.INFEASIBLE:
            issues.append("infeasible")
        elif solved.status is SolverStatus.UNBOUNDED:
            issues.append("unbounded")
        results.append(
            {
                "index": i,
                "path": path,
                "value": float(value),
                "solver_status": solved.status.value,
                "objective_value": obj,
                "primal": solved.primal,
                "feasibility_issues": issues,
            }
        )

    n_opt = sum(1 for r in results if r["solver_status"] == "optimal")
    return {
        "path": path,
        "n_scenarios": len(results),
        "n_optimal": n_opt,
        "scenarios": results,
        "backend": "highs",
    }


def _apply_path(ops: dict[str, Any], path: str, value: float) -> None:
    if path.startswith("constraint:") and path.endswith(".rhs"):
        # constraint:cover.rhs
        mid = path[len("constraint:") : -len(".rhs")]
        for c in ops.get("constraints") or []:
            if c.get("name") == mid:
                c["rhs"] = value
                return
        raise ValueError(f"constraint {mid!r} not found for path {path!r}")
    if path.startswith("objective.coeffs."):
        var = path[len("objective.coeffs.") :]
        coeffs = ops.setdefault("objective", {}).setdefault("coeffs", {})
        coeffs[var] = value
        return
    if path.startswith("variable:") and (path.endswith(".lower") or path.endswith(".upper")):
        # variable:x.lower
        body = path[len("variable:") :]
        name, _, bound = body.rpartition(".")
        for v in ops.get("variables") or []:
            if v.get("name") == name:
                v[bound] = value
                return
        raise ValueError(f"variable {name!r} not found for path {path!r}")
    raise ValueError(
        f"unsupported scenario path {path!r}; "
        "use constraint:<name>.rhs | objective.coeffs.<var> | variable:<name>.lower|upper"
    )


__all__ = ["check_feasibility", "scenario_batch"]
