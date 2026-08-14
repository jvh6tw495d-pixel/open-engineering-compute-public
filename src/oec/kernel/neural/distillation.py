"""Governed tabular teacher→student MLP distillation (Scientific AI S2)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from oec.kernel.neural.training import NORMALIZE_UNSET, predict_mlp, train_mlp
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

_MAX_STUDENT_HIDDEN_LAYERS = 4
_MAX_STUDENT_HIDDEN_WIDTH = 512
_MAX_MLP_PARAMETERS = 1_000_000


def _mlp_parameter_count(model: NeuralModelSpec) -> int:
    widths = [model.input_dim, *model.hidden_dims, model.output_dim]
    return sum(
        in_dim * out_dim + out_dim for in_dim, out_dim in zip(widths[:-1], widths[1:], strict=True)
    )


def _validate_bounded_mlp(model: NeuralModelSpec, *, role: str) -> None:
    hidden = model.hidden_dims
    if (
        len(hidden) > _MAX_STUDENT_HIDDEN_LAYERS
        or any(width > _MAX_STUDENT_HIDDEN_WIDTH for width in hidden)
        or _mlp_parameter_count(model) > _MAX_MLP_PARAMETERS
    ):
        raise ValueError(
            f"S2 {role} MLP exceeds governed cap "
            f"({_MAX_STUDENT_HIDDEN_LAYERS} hidden layers, width <= "
            f"{_MAX_STUDENT_HIDDEN_WIDTH}, parameters <= {_MAX_MLP_PARAMETERS})"
        )


def _validate_governed_teacher_checkpoint(checkpoint: dict[str, Any]) -> None:
    """Validate inline checkpoint structure and its self-consistency digest.

    The digest proves that the supplied serialized state dict has not changed
    relative to its declared value. It is an integrity check, not a signature
    and does not establish cryptographic origin or provenance.
    """
    if checkpoint.get("storage", "json_inline") != "json_inline":
        raise ValueError("S2 teacher_checkpoint must use json_inline storage")
    if checkpoint.get("checkpoint_format_version") != 1:
        raise ValueError("S2 teacher_checkpoint requires governed checkpoint_format_version=1")
    state_dict = checkpoint.get("state_dict")
    if not isinstance(state_dict, dict) or not isinstance(checkpoint.get("model_spec"), dict):
        raise ValueError("S2 teacher_checkpoint requires model_spec and state_dict")
    expected = checkpoint.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("S2 teacher_checkpoint requires a sha256 identity digest")
    canonical = json.dumps(state_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    actual = hashlib.sha256(canonical).hexdigest()
    if actual != expected:
        raise ValueError("S2 teacher_checkpoint sha256 integrity digest mismatch")
    try:
        teacher_model = NeuralModelSpec.model_validate(checkpoint["model_spec"])
    except ValueError as exc:
        raise ValueError("S2 teacher_checkpoint has an invalid MLP model_spec") from exc
    _validate_bounded_mlp(teacher_model, role="teacher")


def _validate_governed_student(student_model: NeuralModelSpec) -> None:
    _validate_bounded_mlp(student_model, role="student")


def distill_mlp(
    dataset: DatasetSpec,
    teacher_checkpoint: dict[str, Any],
    student_model: NeuralModelSpec,
    training: TrainingSpec,
    distillation: DistillationSpec,
    *,
    teacher_normalize: dict[str, list[float]] | None | Any = NORMALIZE_UNSET,
    runtime: TrainingRuntimeSpec | None = None,
) -> NeuralTrainingResult:
    """Train a regression student against a closed blend of teacher and labels.

    This S2 path intentionally supports tabular regression only. ``temperature``
    is recorded for a forward-compatible logits contract; the value must remain
    one for scalar regression because rescaling dimensional engineering targets
    would be physically meaningless.
    """
    _validate_governed_teacher_checkpoint(teacher_checkpoint)
    _validate_governed_student(student_model)
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
