"""ExperimentRecord and experiment-level status (ADR 0034 / W2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from oec.execution.models import ExecutionResult
from oec.experiment.specs import SPEC_SCHEMA_VERSION, ExperimentSpec


class ExperimentStatus(StrEnum):
    """Graded outcome of a multi-step experiment (distinct from ExecutionStatus)."""

    COMPLETED = "COMPLETED"  # all steps acceptable + validation gates pass
    VALIDATION_FAILED = "VALIDATION_FAILED"  # steps ran; metric/status gates failed
    ABORTED = "ABORTED"  # stopped early on INVALID/FAILED step
    FAILED = "FAILED"  # runner/infra error or unexpected exception
    INVALID = "INVALID"  # empty/malformed experiment (e.g. no steps)


class StepRecord(BaseModel):
    """One completed or attempted step inside an experiment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    skill_id: str
    skill_version: str | None = None
    execution: ExecutionResult | None = None
    error: str | None = None


class MetricValue(BaseModel):
    """Resolved metric after reading a path from a step ExecutionResult."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    value: float | None
    path: str
    step_id: str | None
    direction: str
    target: float | None = None
    abs_error_to_target: float | None = None
    error: str | None = None


class ValidationSummary(BaseModel):
    """Experiment-level gate results."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    messages: tuple[str, ...] = ()
    metric_checks: dict[str, bool] = Field(default_factory=dict)


class ProducedArtifact(BaseModel):
    """Artifact written by the experiment store (W2.3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    kind: str
    path: str
    content_hash: str | None = None
    media_type: str | None = None


class ExperimentRecord(BaseModel):
    """Immutable outcome of running an :class:`ExperimentSpec`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = SPEC_SCHEMA_VERSION
    status: ExperimentStatus
    spec: ExperimentSpec
    seed: int
    environment: dict[str, Any] = Field(default_factory=dict)
    steps: tuple[StepRecord, ...] = ()
    metrics: tuple[MetricValue, ...] = ()
    validation: ValidationSummary = Field(
        default_factory=lambda: ValidationSummary(passed=True, messages=())
    )
    artifacts_produced: tuple[ProducedArtifact, ...] = ()
    reproducibility: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        assert isinstance(data, dict)
        return data
