"""Scientific Spec Family v0 (ADR 0035).

These models freeze the *shape* of experiment-oriented contracts. They do not
execute skills. The W2 Experiment Engine will consume ``ExperimentSpec`` and
emit ``ExperimentRecord`` (defined later).

Design rules:

* ``extra="forbid"`` — agent-safe, closed contracts
* ``frozen=True`` — specs are immutable once built
* ``schema_version`` — explicit evolution path
* No torch / pymoo / transformers imports (Core ↛ ML)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SPEC_SCHEMA_VERSION: Literal["0.1.0"] = "0.1.0"


class MetricDirection(StrEnum):
    """Whether larger or smaller metric values are better."""

    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    TARGET = "target"  # closeness to a declared target value


class DatasetKind(StrEnum):
    """Closed catalog of dataset representations in v0."""

    TABULAR_ARRAYS = "tabular_arrays"  # inline x/y (neural-compatible)
    INLINE_JSON = "inline_json"
    PATH_REF = "path_ref"  # local path; no network fetch in v0


class ModelKind(StrEnum):
    """Discriminated model families (extensible by enum only)."""

    NEURAL = "neural"
    SCIENTIFIC_IR = "scientific_ir"
    EXTERNAL_REF = "external_ref"  # opaque id; no auto-download in v0


class ArtifactKind(StrEnum):
    CHECKPOINT = "checkpoint"
    TABLE = "table"
    ARRAY = "array"
    JSON = "json"
    LOG = "log"
    OTHER = "other"


class _SpecBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = SPEC_SCHEMA_VERSION


class DatasetSpec(_SpecBase):
    """General dataset declaration (not neural-only).

    For tabular in-memory arrays (historical neural shape), set
    ``kind=tabular_arrays`` and provide ``x`` / ``y``.
    """

    kind: DatasetKind = DatasetKind.TABULAR_ARRAYS
    # Tabular arrays (optional unless kind requires them)
    x: list[list[float]] | None = None
    y: list[float] | None = None
    val_fraction: float = Field(default=0.0, ge=0.0, lt=1.0)
    # Generic payload / path
    data: dict[str, Any] | None = None
    path: str | None = None
    content_hash: str | None = None
    description: str | None = None

    @field_validator("x")
    @classmethod
    def _x_shape(cls, value: list[list[float]] | None) -> list[list[float]] | None:
        if value is None:
            return value
        if len(value) < 1:
            raise ValueError("dataset x must be non-empty when provided")
        width = len(value[0])
        if width < 1:
            raise ValueError("dataset x rows must have at least 1 feature")
        if any(len(row) != width for row in value):
            raise ValueError("dataset x rows must share the same width")
        return value


class ModelSpec(_SpecBase):
    """Discriminated model declaration.

    ``params`` holds family-specific fields (e.g. neural hidden_dims) as a
    closed JSON object validated by the consuming skill/backend — not free code.
    """

    kind: ModelKind
    name: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class TrainingSpec(_SpecBase):
    """Generic training / search budget knobs (domain-agnostic envelope).

    Neural-specific optimizers/losses remain in ``oec.neural.contracts``;
    this envelope carries cross-domain fields for Experiment composition.
    """

    seed: int = 42
    max_epochs: int | None = Field(default=None, ge=1)
    max_evaluations: int | None = Field(default=None, ge=1)
    budget_seconds: float | None = Field(default=None, gt=0.0)
    early_stopping_patience: int | None = Field(default=None, ge=1)
    # Opaque domain knobs (must be JSON-serializable)
    options: dict[str, Any] = Field(default_factory=dict)


class MetricSpec(_SpecBase):
    """Declarative metric extracted from step ExecutionResult paths."""

    name: str = Field(min_length=1)
    direction: MetricDirection = MetricDirection.MINIMIZE
    # Dotted path into a step result, e.g. "result.rmse" or "diagnostics.loss"
    path: str = Field(min_length=1)
    step_id: str | None = None  # default: last step
    target: float | None = None  # used when direction == TARGET
    # Absolute tolerance for TARGET direction gates (W2.2); None = soft only
    target_abs_tol: float | None = Field(default=None, ge=0.0)
    weight: float = Field(default=1.0, gt=0.0)


class ValidationSpec(_SpecBase):
    """Experiment-level gates (complement skill-level ValidationPolicy)."""

    require_step_status_in: tuple[str, ...] = (
        "VERIFIED",
        "VALIDATED",
        "CONVERGED_WITH_WARNINGS",
        "APPROXIMATE",
    )
    # Metric name → max allowed value (for minimize metrics)
    metric_max: dict[str, float] = Field(default_factory=dict)
    # Metric name → min allowed value (for maximize metrics)
    metric_min: dict[str, float] = Field(default_factory=dict)
    # Metric name → absolute |value - target| max (overrides MetricSpec.target_abs_tol)
    metric_target_abs_tol: dict[str, float] = Field(default_factory=dict)
    # Fail experiment if any declared metric fails to resolve
    require_all_metrics: bool = True
    abort_on_invalid: bool = True
    abort_on_failed: bool = True


class ArtifactSpec(_SpecBase):
    """Expected or produced artifact descriptor."""

    name: str = Field(min_length=1)
    kind: ArtifactKind = ArtifactKind.OTHER
    path: str | None = None
    media_type: str | None = None
    content_hash: str | None = None
    required: bool = False
    description: str | None = None


class ProvenanceSpec(_SpecBase):
    """Policy for what an experiment run must record (not the runtime record)."""

    capture_input_hash: bool = True
    capture_config_hash: bool = True
    capture_backends: bool = True
    capture_git_commit: bool = True
    capture_dependency_versions: bool = True
    capture_environment: bool = True
    extra_keys: tuple[str, ...] = ()


class BindSpec(_SpecBase):
    """Copy a value from a prior step ExecutionResult into this step's inputs.

    ``path`` is a dotted path into the source step's execution dict
    (e.g. ``result.root``). ``as_key`` is the input field name on this step.
    JSON field name for ``as_key`` is ``as`` (serialization alias).
    """

    step_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    as_key: str = Field(min_length=1, serialization_alias="as", validation_alias="as")


class ExperimentStep(_SpecBase):
    """One skill invocation inside an experiment."""

    step_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    skill_version: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    # W2.2: wire prior step outputs into this step's inputs
    binds_from: tuple[BindSpec, ...] = ()


class ExperimentSpec(_SpecBase):
    """Declarative multi-step scientific experiment plan (ADR 0034)."""

    id: str = Field(min_length=1)
    version: str = "0.1.0"
    title: str | None = None
    description: str | None = None
    tags: tuple[str, ...] = ()
    seed: int = 42
    # Environment requirements (informational in v0; enforced in W2)
    required_extras: tuple[str, ...] = ()
    dataset: DatasetSpec | None = None
    model: ModelSpec | None = None
    training: TrainingSpec | None = None
    metrics: tuple[MetricSpec, ...] = ()
    validation: ValidationSpec = Field(default_factory=ValidationSpec)
    artifacts: tuple[ArtifactSpec, ...] = ()
    provenance: ProvenanceSpec = Field(default_factory=ProvenanceSpec)
    steps: tuple[ExperimentStep, ...] = ()

    @field_validator("steps")
    @classmethod
    def _unique_step_ids(cls, value: tuple[ExperimentStep, ...]) -> tuple[ExperimentStep, ...]:
        ids = [s.step_id for s in value]
        if len(ids) != len(set(ids)):
            raise ValueError("ExperimentSpec.steps step_id values must be unique")
        return value
