"""Optimization Specialist v0.1 — formulate OPS, run OEC, narrate results.

This module is the *deterministic harness* of the agent: LLMs may produce
OPS via prompts in ``prompts/``, but numerical answers always come from
:class:`oec.sdk.Engine`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from agents.common import SkillAgentReport, narrate_execution

from oec.execution.models import ExecutionResult, ExecutionStatus
from oec.ops.models import OPSProblem, validate_ops
from oec.ops.schema import OPS_SCHEMA_VERSION
from oec.sdk import Engine

ProblemClass = Literal["lp", "milp", "out_of_scope"]

_SKILL_BY_CLASS: dict[str, str] = {
    "lp": "optimization.lp",
    "milp": "optimization.milp",
}


@dataclass
class SpecialistReport:
    """Full specialist session output (no invented numbers)."""

    problem_class: ProblemClass
    skill_id: str | None
    missing_fields: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    ops: dict[str, Any] | None = None
    ops_valid: bool = False
    validation_error: str | None = None
    execution: ExecutionResult | None = None
    narrative: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_class": self.problem_class,
            "skill_id": self.skill_id,
            "missing_fields": self.missing_fields,
            "assumptions": self.assumptions,
            "ops": self.ops,
            "ops_valid": self.ops_valid,
            "validation_error": self.validation_error,
            "execution": None if self.execution is None else self.execution.model_dump(mode="json"),
            "narrative": self.narrative,
        }


class OptimizationSpecialist:
    """Agent harness: OPS → validate → OEC skill → narrative from result only."""

    def __init__(self, skills_root: str | Path = "skills") -> None:
        self.skills_root = Path(skills_root)
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = Engine(skills_root=self.skills_root)
        return self._engine

    def classify(self, ops_document: dict[str, Any]) -> ProblemClass:
        """Classify from OPS structure (not from free-text heuristics alone)."""
        try:
            problem = validate_ops(ops_document)
        except Exception:
            raw = ops_document.get("problem_class")
            # Schema may still fail later; class label is advisory.
            if raw == "lp":
                return "lp"
            if raw == "milp":
                return "milp"
            return "out_of_scope"
        return problem.problem_class

    def missing_fields(self, ops_document: dict[str, Any]) -> list[str]:
        """Checklist of incomplete OPS fields before solve."""
        missing: list[str] = []
        for key in ("ops_version", "problem_class", "sense", "variables", "objective"):
            if key not in ops_document:
                missing.append(key)
        variables = ops_document.get("variables")
        if not isinstance(variables, list) or not variables:
            missing.append("variables (non-empty)")
        objective = ops_document.get("objective")
        if not isinstance(objective, dict) or "coeffs" not in objective:
            missing.append("objective.coeffs")
        elif isinstance(objective.get("coeffs"), dict) and not objective["coeffs"]:
            # Empty coeffs is allowed but flagged as incomplete intent.
            missing.append("objective.coeffs (empty — confirm pure feasibility problem)")
        return missing

    def validate(self, ops_document: dict[str, Any]) -> OPSProblem:
        return validate_ops(ops_document)

    def execute_ops(self, ops_document: dict[str, Any]) -> SpecialistReport:
        """Full pipeline: classify → validate → run skill → narrate."""
        report = SpecialistReport(
            problem_class=self.classify(ops_document),
            skill_id=None,
            missing_fields=self.missing_fields(ops_document),
            assumptions=list(ops_document.get("assumptions") or []),
            ops=ops_document,
        )

        if report.problem_class == "out_of_scope":
            report.narrative = (
                "Out of scope for Optimization Specialist v0.1 "
                "(need valid OPS with problem_class lp or milp)."
            )
            return report

        if report.missing_fields and any(
            f.split()[0] in {"ops_version", "problem_class", "sense", "variables", "objective"}
            for f in report.missing_fields
            if not f.startswith("objective.coeffs (empty")
        ):
            report.narrative = (
                "Missing required OPS fields: "
                + ", ".join(report.missing_fields)
                + ". Not executing."
            )
            return report

        try:
            problem = self.validate(ops_document)
        except Exception as exc:
            report.validation_error = str(exc)
            report.narrative = f"OPS validation failed: {exc}. Not executing."
            return report

        report.ops_valid = True
        # exclude_none: re-validation via skill must not see JSON nulls for
        # optional fields (jsonschema rejects null where string/number expected).
        report.ops = problem.model_dump(mode="json", exclude_none=True)
        report.assumptions = list(problem.assumptions)
        skill_id = _SKILL_BY_CLASS[problem.problem_class]
        report.skill_id = skill_id

        result = self.engine.run(skill_id, {"ops": report.ops})
        report.execution = result
        report.narrative = self.narrate(report)
        return report

    def narrate(self, report: SpecialistReport) -> str:
        """Build a scientific narrative from validated OPS + ExecutionResult only."""
        if report.execution is None:
            return report.narrative or "No execution result."

        er = report.execution
        lines = [
            f"Skill: {er.skill.id} v{er.skill.version}",
            f"Method: {er.method.id} v{er.method.version}",
            f"Execution status: {er.status.value}",
            f"run_id: {er.run_id}",
        ]
        if er.provenance:
            lines.append(f"input_hash: {er.provenance.get('input_hash', '')}")
            backends = er.provenance.get("backends") or []
            if backends:
                names = ", ".join(f"{b.get('name')}@{b.get('version')}" for b in backends)
                lines.append(f"backends: {names}")

        res = er.result or {}
        if "solver_status" in res:
            lines.append(f"solver_status: {res['solver_status']}")
        if "objective_value" in res:
            lines.append(f"objective_value: {res['objective_value']}")
        if res.get("primal"):
            lines.append(f"primal: {res['primal']}")
        if res.get("feasibility_issues"):
            lines.append("feasibility_issues:")
            for issue in res["feasibility_issues"]:
                lines.append(f"  - {issue}")
        if er.diagnostics:
            lines.append(f"diagnostics: {er.diagnostics}")
        if report.assumptions:
            lines.append("assumptions:")
            for a in report.assumptions:
                lines.append(f"  - {a}")
        if er.status in {ExecutionStatus.INVALID, ExecutionStatus.FAILED}:
            lines.append("No optimal solution is claimed: status is not a successful solve.")
        lines.append(
            "Narrative uses only OEC ExecutionResult fields; "
            "numerical merit of the solve is HiGHS when backend=highs."
        )
        text = "\n".join(lines)
        # Full authority gate (run_id + grounded numbers); same policy as narrate_execution
        from agents.common import assert_narrative_authority

        assert_narrative_authority(text, er)
        return text

    def demo_ops_from_label(self, label: str) -> dict[str, Any]:
        """Return a fixed OPS for golden natural-language *labels* (no LLM).

        Production hosts should replace this with an LLM that emits OPS
        following ``prompts/system.md``. This method only supports a tiny
        catalog for automated acceptance tests.
        """
        key = label.strip().lower()
        if key in {"diet", "diet lp", "min x+y cover"}:
            return {
                "ops_version": OPS_SCHEMA_VERSION,
                "problem_class": "lp",
                "sense": "min",
                "name": "demo_diet",
                "assumptions": ["All variables continuous", "Linear costs and cover constraint"],
                "variables": [
                    {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
                    {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
                ],
                "constraints": [
                    {
                        "name": "cover",
                        "coeffs": {"x": 1, "y": 1},
                        "sense": ">=",
                        "rhs": 1,
                    }
                ],
                "objective": {"coeffs": {"x": 1, "y": 1}},
            }
        if key in {"knapsack", "binary knapsack"}:
            return {
                "ops_version": OPS_SCHEMA_VERSION,
                "problem_class": "milp",
                "sense": "max",
                "name": "demo_knapsack",
                "assumptions": ["Binary items", "Single weight constraint"],
                "variables": [
                    {"name": "a", "kind": "binary"},
                    {"name": "b", "kind": "binary"},
                ],
                "constraints": [
                    {
                        "name": "weight",
                        "coeffs": {"a": 2, "b": 1},
                        "sense": "<=",
                        "rhs": 2,
                    }
                ],
                "objective": {"coeffs": {"a": 3, "b": 2}},
            }
        raise ValueError(
            f"Unknown demo label {label!r}. "
            "Provide a full OPS document or use labels: diet, knapsack."
        )

    def run_demo(self, label: str) -> SpecialistReport:
        """Acceptance path: fixed label → OPS → execute."""
        return self.execute_ops(self.demo_ops_from_label(label))

    def run_skill(self, skill_id: str, inputs: dict[str, Any]) -> SkillAgentReport:
        """Run an explicit ``optimization.*`` skill directly, bypassing OPS
        formulation.

        This is the retry path the MCP discovery fallback
        (``oec.mcp.discovery``) points callers at when a free-text
        ``request`` can't be turned into a full OPS document automatically:
        the caller picks a candidate ``skill_id`` from the suggestion
        payload and adapts its ``example_inputs``. Restricted to
        ``optimization.*`` to keep this specialist's scope honest -- other
        domains have their own agent.
        """
        if not skill_id.startswith("optimization."):
            raise ValueError(
                f"optimization_specialist only accepts optimization.* skills, got {skill_id!r}"
            )
        result = self.engine.run(skill_id, inputs)
        report = SkillAgentReport(
            agent="optimization_specialist",
            skill_id=skill_id,
            inputs=inputs,
            execution=result,
        )
        report.narrative = narrate_execution("optimization_specialist", result)
        return report
