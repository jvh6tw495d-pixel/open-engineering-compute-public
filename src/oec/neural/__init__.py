"""Neural Compute contracts and result DTOs (ADR 0031).

Algorithms live in ``oec.kernel.neural``; PyTorch is an optional extra
(``oec[neural]``). This package is importable without torch.
"""

from __future__ import annotations

from oec.neural.contracts import (
    ActivationName,
    DatasetSpec,
    DeviceSpec,
    LossName,
    NeuralModelSpec,
    NeuralTask,
    OptimizerName,
    OptimizerSpec,
    TrainingSpec,
)
from oec.neural.results import NeuralEvaluationResult, NeuralTrainingResult
from oec.neural.runtime import (
    CheckpointRef,
    DatasetRef,
    TrainingRuntimeSpec,
    estimate_mlp_param_count,
    resolve_capacity,
    resolve_mlp_hidden_dims,
)

__all__ = [
    "ActivationName",
    "CheckpointRef",
    "DatasetRef",
    "DatasetSpec",
    "DeviceSpec",
    "LossName",
    "NeuralEvaluationResult",
    "NeuralModelSpec",
    "NeuralTask",
    "NeuralTrainingResult",
    "OptimizerName",
    "OptimizerSpec",
    "TrainingRuntimeSpec",
    "TrainingSpec",
    "estimate_mlp_param_count",
    "resolve_capacity",
    "resolve_mlp_hidden_dims",
]
