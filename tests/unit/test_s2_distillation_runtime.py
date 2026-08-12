import pytest

pytest.importorskip("torch")

from oec.kernel.neural.distillation import distill_mlp  # noqa: E402
from oec.kernel.neural.training import evaluate_mlp, train_mlp  # noqa: E402
from oec.neural.contracts import (  # noqa: E402
    DatasetSpec,
    DistillationSpec,
    NeuralModelSpec,
    NeuralTask,
    TrainingSpec,
)


def test_distilled_student_checkpoint_evaluates() -> None:
    x = [[float(i)] for i in range(12)]
    y = [2.0 * i + 1.0 for i in range(12)]
    dataset = DatasetSpec(x=x, y=y, val_fraction=0.0)
    teacher = train_mlp(
        dataset,
        NeuralModelSpec(input_dim=1, hidden_dims=[8]),
        TrainingSpec(epochs=80, batch_size=12, seed=3),
    )
    student = distill_mlp(
        dataset,
        teacher.checkpoint,
        NeuralModelSpec(input_dim=1, hidden_dims=[4]),
        TrainingSpec(epochs=80, batch_size=12, seed=4),
        DistillationSpec(temperature=1.0, soft_weight=0.5),
        teacher_normalize=teacher.normalize,
    )
    out = evaluate_mlp(
        x, y, student.checkpoint, task=NeuralTask.REGRESSION, normalize=student.normalize
    )
    assert out.n == len(y)
    assert student.runtime["distillation"]["teacher_checkpoint_supplied"] is True
