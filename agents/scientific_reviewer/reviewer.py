"""Scientific Reviewer v0.1 — independent audit of OPS + ExecutionResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from oec.execution.models import ExecutionResult, ExecutionStatus
from oec.ops.models import validate_ops

_SKILL_FOR_CLASS = {
    "lp": "optimization.lp",
    "milp": "optimization.milp",
}


@dataclass
class CheckResult:
    code: str
    ok: bool
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ReviewReport:
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": [
                {
                    "code": c.code,
                    "ok": c.ok,
                    "message": c.message,
                    "severity": c.severity,
                }
                for c in self.checks
            ],
        }


class ScientificReviewer:
    """Audit OPS + execution without re-solving."""

    def review(
        self,
        ops_document: dict[str, Any] | None,
        execution: ExecutionResult | dict[str, Any],
        *,
        claimed_objective: float | None = None,
        claimed_solver_status: str | None = None,
    ) -> ReviewReport:
        checks: list[CheckResult] = []
        er = (
            execution
            if isinstance(execution, ExecutionResult)
            else ExecutionResult.model_validate(execution)
        )
        result = er.result or {}

        # --- OPS ---
        problem = None
        if ops_document is None:
            checks.append(CheckResult("ops_valid", False, "No OPS document provided for review"))
        else:
            try:
                problem = validate_ops(ops_document)
                checks.append(CheckResult("ops_valid", True, "OPS validates under v0.1"))
            except Exception as exc:
                checks.append(CheckResult("ops_valid", False, f"OPS invalid: {exc}"))

        if problem is not None:
            expected_skill = _SKILL_FOR_CLASS.get(problem.problem_class)
            skill_ok = er.skill.id == expected_skill
            checks.append(
                CheckResult(
                    "class_skill_match",
                    skill_ok,
                    f"skill {er.skill.id!r} vs problem_class {problem.problem_class!r}",
                )
            )

            bounds_ok = True
            for var in problem.variables:
                if var.lower is not None and var.upper is not None and var.lower > var.upper:
                    bounds_ok = False
                    checks.append(
                        CheckResult(
                            "bounds_consistent",
                            False,
                            f"variable {var.name}: lower > upper",
                        )
                    )
            if bounds_ok:
                checks.append(CheckResult("bounds_consistent", True, "No inverted variable bounds"))

            names = {v.name for v in problem.variables}
            obj_unknown = set(problem.objective.coeffs) - names
            checks.append(
                CheckResult(
                    "objective_vars_known",
                    not obj_unknown,
                    "ok" if not obj_unknown else f"unknown objective vars: {sorted(obj_unknown)}",
                )
            )

            cons_bad: list[str] = []
            for cons in problem.constraints:
                unknown = set(cons.coeffs) - names
                if unknown:
                    cons_bad.append(f"{cons.name}:{sorted(unknown)}")
            checks.append(
                CheckResult(
                    "constraint_vars_known",
                    not cons_bad,
                    "ok" if not cons_bad else f"unknown constraint vars {cons_bad}",
                )
            )

            if not problem.assumptions:
                checks.append(
                    CheckResult(
                        "assumptions_present",
                        True,
                        "OPS has empty assumptions (recommended to document)",
                        severity="warning",
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        "assumptions_present",
                        True,
                        f"{len(problem.assumptions)} assumption(s) recorded",
                        severity="warning",
                    )
                )

        # --- ExecutionResult honesty ---
        solver_status = result.get("solver_status")
        status = er.status

        if solver_status == "optimal" and status in {
            ExecutionStatus.INVALID,
            ExecutionStatus.FAILED,
        }:
            checks.append(
                CheckResult(
                    "status_solver_consistency",
                    False,
                    f"solver_status=optimal but OEC status={status.value}",
                )
            )
        elif solver_status in {"infeasible", "unbounded"} and status in {
            ExecutionStatus.VERIFIED,
            ExecutionStatus.VALIDATED,
        }:
            checks.append(
                CheckResult(
                    "status_solver_consistency",
                    False,
                    f"solver_status={solver_status} inconsistent with OEC {status.value}",
                )
            )
        else:
            checks.append(
                CheckResult(
                    "status_solver_consistency",
                    True,
                    f"OEC status={status.value}, solver_status={solver_status!r}",
                )
            )

        # If solver not optimal, converged should be false / status not strong success.
        if solver_status and solver_status != "optimal":
            converged = (er.diagnostics or {}).get("converged")
            ok = converged is False or status not in {
                ExecutionStatus.VERIFIED,
                ExecutionStatus.VALIDATED,
            }
            checks.append(
                CheckResult(
                    "no_false_optimal",
                    ok,
                    "non-optimal solve not marked as strong success"
                    if ok
                    else "non-optimal solver_status with strong OEC success status",
                )
            )
        else:
            checks.append(
                CheckResult("no_false_optimal", True, "No false-optimal pattern detected")
            )

        if solver_status == "infeasible":
            issues = result.get("feasibility_issues") or []
            checks.append(
                CheckResult(
                    "feasibility_on_infeasible",
                    bool(issues) or bool(er.diagnostics),
                    "infeasible carries feasibility_issues or diagnostics"
                    if (issues or er.diagnostics)
                    else "infeasible without diagnostic detail",
                )
            )
        else:
            checks.append(
                CheckResult(
                    "feasibility_on_infeasible",
                    True,
                    "N/A (not infeasible)",
                    severity="warning",
                )
            )

        prov = er.provenance or {}
        prov_ok = bool(er.run_id) and bool(prov.get("input_hash"))
        checks.append(
            CheckResult(
                "provenance_present",
                prov_ok,
                "run_id and input_hash present" if prov_ok else "missing run_id or input_hash",
            )
        )

        if claimed_objective is not None:
            actual = result.get("objective_value")
            match = actual is not None and abs(float(actual) - float(claimed_objective)) < 1e-6
            checks.append(
                CheckResult(
                    "claimed_numbers",
                    match,
                    "claimed_objective matches result"
                    if match
                    else f"claimed_objective={claimed_objective} != result {actual}",
                )
            )
        if claimed_solver_status is not None:
            match = claimed_solver_status == solver_status
            checks.append(
                CheckResult(
                    "claimed_numbers",
                    match,
                    "claimed_solver_status matches"
                    if match
                    else f"claimed {claimed_solver_status!r} != {solver_status!r}",
                )
            )

        # passed iff no failed error-severity checks
        error_fails = [c for c in checks if not c.ok and c.severity == "error"]
        return ReviewReport(passed=not error_fails, checks=checks)
