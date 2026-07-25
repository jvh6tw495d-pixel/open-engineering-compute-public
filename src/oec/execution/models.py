"""Execution-time models: a request into the Skill Execution Service and its result.

``ExecutionResult`` deliberately has no boolean ``success`` field — see
``docs/architecture/adr/0007-validation-status-model.md`` (Sprint 03) for why
execution status is a graded classification, not a pass/fail flag.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from oec.common import VersionedRef


class ExecutionStatus(StrEnum):
    """Graded outcome of a skill execution (plan section 9.4)."""

    VERIFIED = "VERIFIED"
    VALIDATED = "VALIDATED"
    CONVERGED_WITH_WARNINGS = "CONVERGED_WITH_WARNINGS"
    APPROXIMATE = "APPROXIMATE"
    INCONCLUSIVE = "INCONCLUSIVE"
    INVALID = "INVALID"
    FAILED = "FAILED"


class ExecutionRequest(BaseModel):
    """A request to execute a skill with given inputs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_id: str
    skill_version: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    requested_by: str | None = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    seed: int | None = None


class ExecutionResult(BaseModel):
    """The structured, auditable outcome of a skill execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: ExecutionStatus
    skill: VersionedRef
    method: VersionedRef
    inputs: dict[str, Any] = Field(default_factory=dict)
    normalized_inputs: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    conventions: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None
