"""OEC Learning layer (ADR 0043) — contracts first, backends replaceable.

Core-safe: importing this package does not import torch / transformers.
"""

from __future__ import annotations

from oec.learning.capability import capability_matrix, probe_optional
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
from oec.learning.distillation import (
    DistillationConfig,
    DistillationResult,
    compare_base_vs_distilled,
    distill,
)
from oec.learning.environments import (
    ElectricalEngineeringEnvironment,
    MathematicsEnvironment,
    PhysicsEnvironment,
    RewardSpec,
    ToolUseEnvironment,
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
from oec.learning.pipeline import WorkerPipeline, default_worker_dataset
from oec.learning.rl import (
    Action,
    Environment,
    Episode,
    Policy,
    ReinforcementTrainer,
    RLResult,
    State,
    Trajectory,
)
from oec.learning.suite import (
    agentic_benchmark,
    backend_benchmark,
    compare_backend_runs,
    declared_backends,
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
    "Action",
    "DistillationConfig",
    "DistillationResult",
    "ElectricalEngineeringEnvironment",
    "Environment",
    "Episode",
    "MathematicsEnvironment",
    "PhysicsEnvironment",
    "Policy",
    "RLResult",
    "ReinforcementTrainer",
    "RewardSpec",
    "State",
    "ToolUseEnvironment",
    "Trajectory",
    "WorkerPipeline",
    "agentic_benchmark",
    "backend_benchmark",
    "capability_matrix",
    "compare_backend_runs",
    "compare_base_vs_distilled",
    "compare_results",
    "compute_dataset_hash",
    "declared_backends",
    "default_worker_dataset",
    "distill",
    "evaluate_metrics",
    "probe_optional",
    "run_learning_experiment",
    "select_backend",
    "split_records",
]
