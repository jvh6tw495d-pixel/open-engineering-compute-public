"""Experiment infrastructure (ADR 0034 / ADR 0035).

W0: declarative specs. W2: sequential ``run_experiment`` + ``ExperimentRecord``.
"""

from __future__ import annotations

from oec.experiment.record import (
    ExperimentRecord,
    ExperimentStatus,
    MetricValue,
    StepRecord,
    ValidationSummary,
)
from oec.experiment.runner import config_hash, run_experiment
from oec.experiment.specs import (
    SPEC_SCHEMA_VERSION,
    ArtifactSpec,
    DatasetSpec,
    ExperimentSpec,
    ExperimentStep,
    MetricSpec,
    ModelSpec,
    ProvenanceSpec,
    TrainingSpec,
    ValidationSpec,
)

__all__ = [
    "SPEC_SCHEMA_VERSION",
    "ArtifactSpec",
    "DatasetSpec",
    "ExperimentRecord",
    "ExperimentSpec",
    "ExperimentStatus",
    "ExperimentStep",
    "MetricSpec",
    "MetricValue",
    "ModelSpec",
    "ProvenanceSpec",
    "StepRecord",
    "TrainingSpec",
    "ValidationSpec",
    "ValidationSummary",
    "config_hash",
    "run_experiment",
]
