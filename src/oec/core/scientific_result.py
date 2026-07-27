"""ScientificResult — additive public scientific outcome (v2.0 kernel).

Does not replace :class:`~oec.execution.models.ExecutionResult`. Prefer
:func:`from_execution_result` for interoperability with the Skill Engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from oec.core.diagnostics import Diagnostic, diagnostics_from_mapping
from oec.core.provenance import ProvenanceRecord
from oec.core.types import Assumption, BackendRef, MethodRef
from oec.core.validity import ValidityDomain
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
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    # Raw legacy mapping retained for full fidelity with ExecutionResult
    diagnostics_raw: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecord = Field(default_factory=ProvenanceRecord)
    validity: ValidityDomain | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None

    @property
    def backends(self) -> list[BackendRef]:
        return list(self.provenance.backends)

    @property
    def backend_names(self) -> list[str]:
        return [b.name for b in self.backends]


def from_execution_result(
    er: ExecutionResult,
    *,
    validity: ValidityDomain | None = None,
) -> ScientificResult:
    """Map Skill Engine result → ScientificResult without mutation."""
    assumptions = [
        Assumption(text=a, source="execution")
        for a in (er.assumptions or [])
        if isinstance(a, str) and a.strip()
    ]
    raw_diag = dict(er.diagnostics or {})
    return ScientificResult(
        run_id=er.run_id,
        status=er.status,
        skill_id=er.skill.id,
        skill_version=er.skill.version,
        method=MethodRef(id=er.method.id, version=er.method.version),
        value=dict(er.result or {}),
        assumptions=assumptions,
        diagnostics=diagnostics_from_mapping(raw_diag),
        diagnostics_raw=raw_diag,
        warnings=list(er.warnings or []),
        validation=dict(er.validation or {}),
        provenance=ProvenanceRecord.from_mapping(dict(er.provenance or {})),
        validity=validity,
        started_at=er.started_at,
        completed_at=er.completed_at,
        duration_ms=er.duration_ms,
    )
