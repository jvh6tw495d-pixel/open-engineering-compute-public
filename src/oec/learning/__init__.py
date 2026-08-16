"""OEC Learning layer (ADR 0043) — contracts first, backends replaceable.

Core-safe: importing this package does not import torch / transformers.
"""

from __future__ import annotations

from oec.learning.bootstrap import (
    BootstrapReport,
    bootstrap_status,
    learning_envs_root,
    plan_bootstrap,
    run_bootstrap,
)
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
    compute_run_identity,
    run_learning_experiment,
    select_backend,
)
from oec.learning.hardware import capture_dependency_versions
from oec.learning.install_hints import (
    ART_MISSING,
    ART_PYPI,
    ART_WRONG_PACKAGE,
    AXOLOTL_MISSING,
    HF_MISSING,
    UNSLOTH_MISSING,
    hint_for,
)
from oec.learning.pipeline import WorkerPipeline, default_worker_dataset, payload_from_execution
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
from oec.learning.store import (
    ReplayReport,
    load_dataset,
    load_run,
    replay_learning_experiment,
    save_dataset,
    save_run,
)
from oec.learning.suite import (
    agentic_benchmark,
    backend_benchmark,
    compare_backend_runs,
    declared_backends,
    measure_capability_suite,
)
from oec.learning.verifiers import (
    execution_result_reward,
    execution_result_scores,
    reward_from_execution,
    scores_from_execution,
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
    "ReplayReport",
    "RewardSpec",
    "State",
    "ToolUseEnvironment",
    "Trajectory",
    "WorkerPipeline",
    "ART_MISSING",
    "ART_PYPI",
    "ART_WRONG_PACKAGE",
    "AXOLOTL_MISSING",
    "BootstrapReport",
    "HF_MISSING",
    "UNSLOTH_MISSING",
    "bootstrap_status",
    "hint_for",
    "learning_envs_root",
    "plan_bootstrap",
    "run_bootstrap",
    "agentic_benchmark",
    "backend_benchmark",
    "capability_matrix",
    "compare_backend_runs",
    "compare_base_vs_distilled",
    "capture_dependency_versions",
    "compare_results",
    "compute_dataset_hash",
    "compute_run_identity",
    "declared_backends",
    "default_worker_dataset",
    "distill",
    "evaluate_metrics",
    "execution_result_reward",
    "execution_result_scores",
    "load_dataset",
    "load_run",
    "measure_capability_suite",
    "payload_from_execution",
    "probe_optional",
    "replay_learning_experiment",
    "reward_from_execution",
    "run_learning_experiment",
    "save_dataset",
    "save_run",
    "scores_from_execution",
    "select_backend",
    "split_records",
]
