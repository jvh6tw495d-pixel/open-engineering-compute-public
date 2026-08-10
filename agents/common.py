"""Shared agent harness: run OEC skills and narrate only from ExecutionResult.

Authority policy (P0 / ADR 0023 spirit):

* Every successful narrative **must** cite ``execution.run_id``.
* Numeric tokens in the narrative must come from ``ExecutionResult`` fields
  (see ``benchmarks.agent_metrics.narrative_invented_numbers``).
* Agents never invent scientific numbers; backends own merit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from oec.execution.models import ExecutionResult, ExecutionStatus
from oec.sdk import Engine


@dataclass
class SkillAgentReport:
    agent: str
    skill_id: str | None
    inputs: dict[str, Any] | None = None
    execution: ExecutionResult | None = None
    narrative: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "skill_id": self.skill_id,
            "inputs": self.inputs,
            "execution": None if self.execution is None else self.execution.model_dump(mode="json"),
            "narrative": self.narrative,
            "notes": self.notes,
        }


def narrative_cites_run_id(narrative: str, run_id: str) -> bool:
    """True if *narrative* contains the full *run_id* token."""
    if not run_id or not narrative:
        return False
    return run_id in narrative


def narrative_authority_violations(narrative: str, execution: ExecutionResult) -> list[str]:
    """Return human-readable authority policy violations (empty = pass).

    Rules:
    1. Narrative must include ``execution.run_id`` (no number without provenance).
    2. Numeric tokens must be grounded in ExecutionResult (invented-number rate 0).
    """
    violations: list[str] = []
    if not narrative_cites_run_id(narrative, execution.run_id):
        violations.append(
            f"narrative missing run_id {execution.run_id!r} "
            "(policy: no number / claim without run_id)"
        )
    # Lazy import: benchmarks is repo-root companion, not part of the oec wheel
    try:
        from benchmarks.agent_metrics import narrative_invented_numbers
    except ImportError:
        return violations
    invented = narrative_invented_numbers(narrative, execution)
    if invented:
        violations.append(f"invented numeric tokens not in ExecutionResult: {invented}")
    return violations


def assert_narrative_authority(narrative: str, execution: ExecutionResult) -> None:
    """Raise ``AssertionError`` if narrative fails the run_id / invented-number policy."""
    viol = narrative_authority_violations(narrative, execution)
    if viol:
        raise AssertionError("; ".join(viol))


def narrate_execution(agent: str, execution: ExecutionResult) -> str:
    """Build a narrative **only** from ExecutionResult fields; always cites run_id."""
    lines = [
        f"Agent: {agent}",
        f"Skill: {execution.skill.id} v{execution.skill.version}",
        f"Method: {execution.method.id} v{execution.method.version}",
        f"Status: {execution.status.value}",
        f"run_id: {execution.run_id}",
    ]
    if execution.provenance:
        lines.append(f"input_hash: {execution.provenance.get('input_hash', '')}")
    if execution.result:
        lines.append(f"result: {execution.result}")
    if execution.diagnostics:
        lines.append(f"diagnostics: {execution.diagnostics}")
    if execution.warnings:
        lines.append(f"warnings: {execution.warnings}")
    if execution.status in {ExecutionStatus.INVALID, ExecutionStatus.FAILED}:
        lines.append("No successful scientific outcome claimed.")
    lines.append("Narrative uses only ExecutionResult fields; backends own numerical merit.")
    text = "\n".join(lines)
    # Self-check: harness must never emit a narrative without run_id
    assert narrative_cites_run_id(text, execution.run_id), "narrate_execution omitted run_id"
    return text


class SkillSpecialist:
    """Base specialist: map demo labels → skill+inputs, run Engine, narrate."""

    name: str = "skill_specialist"
    demos: dict[str, tuple[str, dict[str, Any]]] = {}

    def __init__(self, skills_root: str | Path = "skills") -> None:
        self.skills_root = Path(skills_root)
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = Engine(skills_root=self.skills_root)
        return self._engine

    def run_skill(self, skill_id: str, inputs: dict[str, Any]) -> SkillAgentReport:
        result = self.engine.run(skill_id, inputs)
        report = SkillAgentReport(
            agent=self.name,
            skill_id=skill_id,
            inputs=inputs,
            execution=result,
        )
        report.narrative = narrate_execution(self.name, result)
        return report

    def run_demo(self, label: str) -> SkillAgentReport:
        key = label.strip().lower()
        if key not in self.demos:
            raise ValueError(f"Unknown demo {label!r} for {self.name}. Known: {sorted(self.demos)}")
        skill_id, inputs = self.demos[key]
        report = self.run_skill(skill_id, inputs)
        report.notes.append(f"demo_label={key}")
        return report
