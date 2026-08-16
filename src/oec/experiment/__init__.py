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
from oec.experiment.cross_domain import (
    build_distill_then_eval_experiment,
    build_evo_sphere_experiment,
    build_foundation_embed_then_stats_experiment,
    build_full_stack_learning_experiment,
    build_monte_carlo_then_describe_experiment,
    build_peft_train_then_generate_experiment,
    build_physics_kinematics_experiment,
    build_physics_to_neural_surrogate_experiment,
    build_root_bind_to_distribution_experiment,
    build_wave_then_stats_experiment,
    get_cross_domain_builder,
    list_cross_domain_builders,
)
from oec.experiment.evolutionary import (
    PopulationSpec,
    build_evo_then_describe_experiment,
    build_hybrid_training_experiment,
    build_nsga2_experiment,
    build_optimize_single_experiment,
    problem_to_optimize_inputs,
    sphere_problem_2d,
)
from oec.experiment.neural import (
    build_mlp_regressor_experiment,
    build_neural_training_mode_experiment,
    mlp_regressor_inputs,
    neural_dataset_to_inputs,
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
    "PopulationSpec",
    "ProducedArtifact",
    "ProvenanceSpec",
    "StepRecord",
    "TrainingSpec",
    "ValidationSpec",
    "ValidationSummary",
    "build_distill_then_eval_experiment",
    "build_evo_sphere_experiment",
    "build_full_stack_learning_experiment",
    "build_evo_then_describe_experiment",
    "build_foundation_embed_then_stats_experiment",
    "build_hybrid_training_experiment",
    "build_mlp_regressor_experiment",
    "build_monte_carlo_then_describe_experiment",
    "build_neural_training_mode_experiment",
    "build_nsga2_experiment",
    "build_optimize_single_experiment",
    "build_peft_train_then_generate_experiment",
    "build_physics_kinematics_experiment",
    "build_physics_to_neural_surrogate_experiment",
    "build_root_bind_to_distribution_experiment",
    "build_wave_then_stats_experiment",
    "config_hash",
    "default_artifact_root",
    "get_cross_domain_builder",
    "list_cross_domain_builders",
    "load_experiment_record",
    "mlp_regressor_inputs",
    "neural_dataset_to_inputs",
    "persist_experiment_record",
    "problem_to_optimize_inputs",
    "run_experiment",
    "sphere_problem_2d",
]
