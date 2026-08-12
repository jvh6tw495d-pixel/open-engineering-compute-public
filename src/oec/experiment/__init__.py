"""Experiment infrastructure (framework W0 specs; W2 runner).

Specs are declarative contracts. Runtime orchestration lands in W2
(``run_experiment``). See ADR 0034 and ADR 0035.
"""

from __future__ import annotations

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
    "ExperimentSpec",
    "ExperimentStep",
    "MetricSpec",
    "ModelSpec",
    "ProvenanceSpec",
    "TrainingSpec",
    "ValidationSpec",
]
