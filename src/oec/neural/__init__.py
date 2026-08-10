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

__all__ = [
    "ActivationName",
    "DatasetSpec",
    "DeviceSpec",
    "LossName",
    "NeuralEvaluationResult",
    "NeuralModelSpec",
    "NeuralTask",
    "NeuralTrainingResult",
    "OptimizerName",
    "OptimizerSpec",
    "TrainingSpec",
]
