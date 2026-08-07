"""Shared agent harness: run OEC skills and narrate only from ExecutionResult."""

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


def narrate_execution(agent: str, execution: ExecutionResult) -> str:
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
    return "\n".join(lines)


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
