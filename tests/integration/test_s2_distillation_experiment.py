"""S2 live distill→evaluate experiment regression (requires oec[neural])."""

from __future__ import annotations

import pytest

from oec.experiment import ExperimentStatus
from oec.experiment.cross_domain import build_distill_then_eval_experiment
from oec.kernel.neural.training import train_mlp
from oec.neural.contracts import DatasetSpec, NeuralModelSpec, TrainingSpec
from oec.sdk import Engine

pytest.importorskip("torch")
pytestmark = pytest.mark.neural


def test_s2_distill_then_eval_experiment_completes() -> None:
    x = [[float(i)] for i in range(8)]
    y = [2.0 * float(i) + 1.0 for i in range(8)]
    dataset = DatasetSpec(x=x, y=y, val_fraction=0.0)
    teacher = train_mlp(
        dataset,
        NeuralModelSpec(input_dim=1, hidden_dims=[4]),
        TrainingSpec(epochs=8, batch_size=8, seed=3),
    )
    spec = build_distill_then_eval_experiment(
        teacher_checkpoint=teacher.checkpoint,
        x=x,
        y=y,
        student_hidden_dims=[4],
        epochs=8,
        seed=5,
    )

    record = Engine(skills_root="skills").run_experiment(spec)

    assert record.status is ExperimentStatus.COMPLETED
    assert [step.execution.status.value for step in record.steps if step.execution] == [
        "VALIDATED",
        "VERIFIED",
    ]
