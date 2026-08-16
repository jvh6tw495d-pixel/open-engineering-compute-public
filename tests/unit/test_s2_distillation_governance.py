"""S2 gate conditions: governed teacher identity, bounded student, and end-to-end builder."""

from __future__ import annotations

import pytest

pytest.importorskip("torch")

from oec.kernel.neural.distillation import distill_mlp  # noqa: E402
from oec.kernel.neural.training import train_mlp  # noqa: E402
from oec.neural.contracts import (  # noqa: E402
    DatasetSpec,
    DistillationSpec,
    NeuralModelSpec,
    TrainingSpec,
)


def _teacher() -> tuple[DatasetSpec, object]:
    dataset = DatasetSpec(x=[[float(i)] for i in range(6)], y=[2.0 * i + 1.0 for i in range(6)])
    teacher = train_mlp(
        dataset,
        NeuralModelSpec(input_dim=1, hidden_dims=[4]),
        TrainingSpec(epochs=3, batch_size=6, seed=4),
    )
    return dataset, teacher


def test_distill_rejects_teacher_without_oec_checkpoint_identity() -> None:
    dataset, teacher = _teacher()
    checkpoint = dict(teacher.checkpoint)
    checkpoint.pop("checkpoint_format_version", None)
    with pytest.raises(ValueError, match="format|identity|governed"):
        distill_mlp(
            dataset,
            checkpoint,
            NeuralModelSpec(input_dim=1, hidden_dims=[4]),
            TrainingSpec(epochs=2, batch_size=6),
            DistillationSpec(),
        )


def test_distill_rejects_teacher_checkpoint_digest_tamper() -> None:
    dataset, teacher = _teacher()
    checkpoint = dict(teacher.checkpoint)
    checkpoint["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="sha256|digest|identity"):
        distill_mlp(
            dataset,
            checkpoint,
            NeuralModelSpec(input_dim=1, hidden_dims=[4]),
            TrainingSpec(epochs=2, batch_size=6),
            DistillationSpec(),
        )


def test_distill_rejects_student_architecture_above_governed_cap() -> None:
    dataset, teacher = _teacher()
    with pytest.raises(ValueError, match="hidden|governed|cap"):
        distill_mlp(
            dataset,
            teacher.checkpoint,
            NeuralModelSpec(input_dim=1, hidden_dims=[1024, 1024, 1024, 1024, 1024]),
            TrainingSpec(epochs=2, batch_size=6),
            DistillationSpec(),
        )


def test_distill_rejects_teacher_model_above_governed_parameter_cap_before_build() -> None:
    dataset, teacher = _teacher()
    checkpoint = dict(teacher.checkpoint)
    checkpoint["model_spec"] = {
        "architecture": "mlp",
        "input_dim": 512,
        "output_dim": 1,
        "hidden_dims": [512, 512, 512, 512],
        "activation": "relu",
        "dropout": 0.0,
    }
    with pytest.raises(ValueError, match="teacher.*cap|governed"):
        distill_mlp(
            dataset,
            checkpoint,
            NeuralModelSpec(input_dim=1, hidden_dims=[4]),
            TrainingSpec(epochs=2, batch_size=6),
            DistillationSpec(),
        )
