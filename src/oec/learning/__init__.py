"""OEC Learning layer (ADR 0043) — contracts first, backends replaceable.

Core-safe: importing this package does not import torch / transformers.
"""

from __future__ import annotations

from oec.learning.contracts import (
    ArtifactRef,
    FineTuneBackend,
    FineTuneBackendName,
    MetricDirection,
    MetricSpec,
    ModelFamily,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
)
from oec.learning.datasets import (
    DatasetKind,
    DatasetProvenance,
    DatasetSplit,
    LearningDataset,
    compute_dataset_hash,
    split_records,
)
from oec.learning.errors import (
    BackendNotAvailableError,
    BenchmarkError,
    DatasetIntegrityError,
    LearningError,
)
from oec.learning.evaluation import (
    Benchmark,
    EvaluationResult,
    GoldenCase,
    compare_results,
    evaluate_metrics,
)
from oec.learning.experiments import (
    LearningExperiment,
    LearningRunRecord,
    run_learning_experiment,
    select_backend,
)

__all__ = [
    "ArtifactRef",
    "BackendNotAvailableError",
    "Benchmark",
    "BenchmarkError",
    "DatasetIntegrityError",
    "DatasetKind",
    "DatasetProvenance",
    "DatasetSplit",
    "EvaluationResult",
    "FineTuneBackend",
    "FineTuneBackendName",
    "GoldenCase",
    "LearningDataset",
    "LearningError",
    "LearningExperiment",
    "LearningRunRecord",
    "MetricDirection",
    "MetricSpec",
    "ModelFamily",
    "ModelRef",
    "TrainingConfig",
    "TrainingMethod",
    "TrainingResult",
    "compare_results",
    "compute_dataset_hash",
    "evaluate_metrics",
    "run_learning_experiment",
    "select_backend",
    "split_records",
]
