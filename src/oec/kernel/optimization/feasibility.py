"""Feasibility diagnostics for linear OPS (S7′). Backend merit: HiGHS.

``explain_infeasibility`` is an **experimental heuristic**, not a certified IIS
finder (A23-02).
"""

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
    """Check LP/MILP feasibility without claiming an optimal business objective."""
    problem = validate_ops(ops_document)
    variables, constraints, sense = ops_to_linear_parts(problem)

    issues: list[str] = list(check_bound_conflicts(variables))
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
        msg_issues.append(
            "HiGHS reported the problem as unbounded under zero objective"
        )
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
    """Sweep a numeric field in OPS and re-solve each scenario (S7′ v0)."""
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
    if path.startswith("variable:") and (
        path.endswith(".lower") or path.endswith(".upper")
    ):
        body = path[len("variable:") :]
        name, _, bound = body.rpartition(".")
        for v in ops.get("variables") or []:
            if v.get("name") == name:
                v[bound] = value
                return
        raise ValueError(f"variable {name!r} not found for path {path!r}")
    raise ValueError(
        f"unsupported scenario path {path!r}; "
        "use constraint:<name>.rhs | objective.coeffs.<var> | "
        "variable:<name>.lower|upper"
    )


def explain_infeasibility(
    ops_document: dict[str, Any],
    *,
    max_drop_one_solves: int = 50,
) -> dict[str, Any]:
    """Heuristic explanation of LP infeasibility (experimental, not a certified IIS).

    Tiers
    -----
    1. ``precheck`` — bound conflicts / empty-coefficient constraints.
    2. ``feasible`` — zero-objective solve is optimal.
    3. ``solver_unavailable`` / ``time_limit`` / ``unknown`` — solver outcomes.
    4. ``single_constraint_relaxation`` — drop-one scan: names of constraints
       whose *individual* removal makes the remainder feasible.

    The drop-one list is **not** claimed to be irreducible, smallest, or an IIS.
    If no single removal restores feasibility, the list is empty and the
    explanation states that fact explicitly (A23-02).
    """
    problem = validate_ops(ops_document)
    variables, constraints, _sense = ops_to_linear_parts(problem)

    issues: list[str] = list(check_bound_conflicts(variables))
    empty_constraints = [c.name for c in constraints if not c.coeffs]
    for name in empty_constraints:
        issues.append(f"constraint {name!r} has no coefficients")

    base_fields: dict[str, Any] = {
        "bound_conflicts": list(issues) if issues else [],
        "empty_constraints": empty_constraints,
        "single_constraint_relaxations": [],
        # Backward-compatible alias (same list; not an IIS claim)
        "iis_candidate_constraints": [],
        "n_constraints": len(constraints),
        "heuristic": "drop_one_constraint",
        "claims_iis": False,
        "max_drop_one_solves": int(max_drop_one_solves),
        "drop_one_solves_used": 0,
    }

    if issues:
        return {
            "feasible": False,
            "status": "infeasible",
            "tier": "precheck",
            "explanation": (
                "Bound conflicts and/or empty-coefficient constraints make the "
                "model infeasible without solving. This is not an IIS certificate."
            ),
            **base_fields,
            "backend": "precheck",
        }

    time_limit = problem.execution_limits.time_limit_seconds
    zero_obj_vars = [
        LinearVariable(
            name=v.name,
            lower=v.lower,
            upper=v.upper,
            kind=v.kind,
            objective_coeff=0.0,
        )
        for v in variables
    ]
    try:
        baseline = solve_linear(
            variables=zero_obj_vars,
            constraints=constraints,
            sense="min",
            time_limit_seconds=time_limit,
        )
    except HighsNotAvailableError as exc:
        return {
            "feasible": False,
            "status": "solver_unavailable",
            "tier": "solver_unavailable",
            "explanation": exc.message,
            **base_fields,
            "backend": "highs",
        }

    if baseline.status is SolverStatus.OPTIMAL:
        return {
            "feasible": True,
            "status": "feasible",
            "tier": "feasible",
            "explanation": "the model is feasible under a zero-objective solve.",
            **base_fields,
            "backend": "highs",
        }

    if baseline.status is SolverStatus.TIME_LIMIT:
        return {
            "feasible": False,
            "status": "time_limit",
            "tier": "time_limit",
            "explanation": (
                "baseline feasibility solve hit the time limit; "
                "infeasibility is not certified."
            ),
            **base_fields,
            "backend": "highs",
        }

    if baseline.status is not SolverStatus.INFEASIBLE:
        return {
            "feasible": False,
            "status": "unknown",
            "tier": "unknown",
            "explanation": (
                f"baseline solve returned {baseline.status.value}; "
                "cannot classify infeasibility."
            ),
            **base_fields,
            "backend": "highs",
        }

    # Drop-one heuristic (budgeted).
    relaxable: list[str] = []
    solves_used = 0
    budget = max(0, int(max_drop_one_solves))
    for i, trial in enumerate(constraints):
        if solves_used >= budget:
            break
        subset = constraints[:i] + constraints[i + 1 :]
        try:
            attempt = solve_linear(
                variables=zero_obj_vars,
                constraints=subset,
                sense="min",
                time_limit_seconds=time_limit,
            )
        except HighsNotAvailableError as exc:
            return {
                "feasible": False,
                "status": "solver_unavailable",
                "tier": "solver_unavailable",
                "explanation": exc.message,
                **base_fields,
                "backend": "highs",
            }
        solves_used += 1
        if attempt.status is SolverStatus.OPTIMAL:
            relaxable.append(trial.name)

    base_fields["single_constraint_relaxations"] = relaxable
    base_fields["iis_candidate_constraints"] = list(relaxable)
    base_fields["drop_one_solves_used"] = solves_used

    if relaxable:
        explanation = (
            "HiGHS reported infeasibility. Dropping any *one* of the listed "
            "constraints individually restores feasibility in a zero-objective "
            "solve (drop-one heuristic). This list is NOT proven irreducible "
            "and is NOT a certified IIS; multiple independent conflicts may "
            "exist outside this list."
        )
        tier = "single_constraint_relaxation"
    elif solves_used < len(constraints) and solves_used >= budget:
        explanation = (
            "HiGHS reported infeasibility, but the drop-one scan hit its solve "
            f"budget ({budget}) before testing every constraint. No complete "
            "single-constraint relaxation list is available."
        )
        tier = "budget_exhausted"
    else:
        explanation = (
            "HiGHS reported infeasibility, and removing any *single* constraint "
            "does not restore feasibility. The conflict likely involves multiple "
            "constraints jointly (or bounds already checked). No IIS certificate "
            "is provided by this heuristic."
        )
        tier = "no_single_relaxation"

    return {
        "feasible": False,
        "status": "infeasible",
        "tier": tier,
        "explanation": explanation,
        **base_fields,
        "backend": "highs",
    }


__all__ = ["check_feasibility", "scenario_batch", "explain_infeasibility"]
