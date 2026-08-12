"""Experiment infrastructure (ADR 0034 / ADR 0035).

W0: declarative specs.
W2: sequential ``run_experiment``, metrics/gates, binds, artifacts, surfaces.
"""

from __future__ import annotations

from oec.experiment.artifacts import (
    default_artifact_root,
    load_experiment_record,
    persist_experiment_record,
)
from oec.experiment.record import (
    ExperimentRecord,
    ExperimentStatus,
    MetricValue,
    ProducedArtifact,
    StepRecord,
    ValidationSummary,
)
from oec.experiment.runner import config_hash, run_experiment
from oec.experiment.specs import (
    SPEC_SCHEMA_VERSION,
    ArtifactSpec,
    BindSpec,
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
    "BindSpec",
    "DatasetSpec",
    "ExperimentRecord",
    "ExperimentSpec",
    "ExperimentStatus",
    "ExperimentStep",
    "MetricSpec",
    "MetricValue",
    "ModelSpec",
    "ProducedArtifact",
    "ProvenanceSpec",
    "StepRecord",
    "TrainingSpec",
    "ValidationSpec",
    "ValidationSummary",
    "config_hash",
    "default_artifact_root",
    "load_experiment_record",
    "persist_experiment_record",
    "run_experiment",
]
