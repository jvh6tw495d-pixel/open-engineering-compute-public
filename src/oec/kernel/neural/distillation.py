"""Governed tabular teacher→student MLP distillation (Scientific AI S2)."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.neural.training import predict_mlp, train_mlp
from oec.neural.contracts import (
    DatasetSpec,
    DistillationLossMix,
    DistillationSpec,
    NeuralModelSpec,
    NeuralTask,
    TrainingSpec,
)
from oec.neural.results import NeuralTrainingResult
from oec.neural.runtime import TrainingRuntimeSpec


def distill_mlp(
    dataset: DatasetSpec,
    teacher_checkpoint: dict[str, Any],
    student_model: NeuralModelSpec,
    training: TrainingSpec,
    distillation: DistillationSpec,
    *,
    teacher_normalize: dict[str, list[float]] | None = None,
    runtime: TrainingRuntimeSpec | None = None,
) -> NeuralTrainingResult:
    """Train a regression student against a closed blend of teacher and labels.

    This S2 path intentionally supports tabular regression only. ``temperature``
    is recorded for a forward-compatible logits contract; the value must remain
    one for scalar regression because rescaling dimensional engineering targets
    would be physically meaningless.
    """
    if teacher_checkpoint.get("storage", "json_inline") != "json_inline":
        raise ValueError("S2 teacher_checkpoint must use json_inline storage")
    if training.task is not NeuralTask.REGRESSION:
        raise ValueError("S2 tabular distillation currently supports regression only")
    if distillation.temperature != 1.0:
        raise ValueError("temperature must be 1.0 for scalar regression distillation")
    if student_model.input_dim != len(dataset.x[0]):
        raise ValueError("student input_dim must match dataset feature width")

    teacher = np.asarray(
        predict_mlp(
            dataset.x,
            teacher_checkpoint,
            normalize=teacher_normalize,
            device=training.device.device,
        ),
        dtype=float,
    ).reshape(-1)
    observed = np.asarray(dataset.y, dtype=float)
    if teacher.shape != observed.shape:
        raise ValueError("teacher predictions must match dataset target shape")
    if distillation.loss_mix is DistillationLossMix.SOFT_ONLY:
        student_y = teacher
    else:
        student_y = distillation.soft_weight * teacher + (1.0 - distillation.soft_weight) * observed

    result = train_mlp(
        DatasetSpec(x=dataset.x, y=student_y.tolist(), val_fraction=dataset.val_fraction),
        student_model,
        training,
        runtime=runtime,
    )
    return result.model_copy(
        update={
            "runtime": {
                **(result.runtime or {}),
                "distillation": {
                    "teacher_checkpoint_supplied": True,
                    "temperature": distillation.temperature,
                    "loss_mix": distillation.loss_mix.value,
                    "soft_weight": distillation.soft_weight,
                },
            }
        }
    )
