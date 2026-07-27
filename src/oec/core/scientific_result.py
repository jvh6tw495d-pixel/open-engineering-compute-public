"""ScientificResult — additive public scientific outcome (V3 roadmap §2.4 / v2.0).

Does not replace :class:`~oec.execution.models.ExecutionResult`. Prefer
:func:`from_execution_result` for interoperability with the Skill Engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from oec.core.types import Assumption, BackendRef, MethodRef
from oec.execution.models import ExecutionResult, ExecutionStatus


class ScientificResult(BaseModel):
    """Structured scientific outcome independent of domain skill packages."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    status: ExecutionStatus
    skill_id: str
    skill_version: str
    method: MethodRef
    value: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[Assumption] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    backends: list[BackendRef] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None

    @property
    def backend_names(self) -> list[str]:
        return [b.name for b in self.backends]


def from_execution_result(er: ExecutionResult) -> ScientificResult:
    """Map Skill Engine result → ScientificResult without mutation."""
    assumptions = [
        Assumption(text=a, source="execution")
        for a in (er.assumptions or [])
        if isinstance(a, str) and a.strip()
    ]
    backends: list[BackendRef] = []
    raw_backends = (er.provenance or {}).get("backends") or []
    if isinstance(raw_backends, list):
        for item in raw_backends:
            if isinstance(item, dict) and item.get("name"):
                backends.append(
                    BackendRef(
                        name=str(item["name"]),
                        version=None if item.get("version") is None else str(item["version"]),
                    )
                )
    return ScientificResult(
        run_id=er.run_id,
        status=er.status,
        skill_id=er.skill.id,
        skill_version=er.skill.version,
        method=MethodRef(id=er.method.id, version=er.method.version),
        value=dict(er.result or {}),
        assumptions=assumptions,
        diagnostics=dict(er.diagnostics or {}),
        warnings=list(er.warnings or []),
        validation=dict(er.validation or {}),
        provenance=dict(er.provenance or {}),
        backends=backends,
        started_at=er.started_at,
        completed_at=er.completed_at,
        duration_ms=er.duration_ms,
    )
