"""neural.distill — governed tabular teacher→student MLP distillation."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.distillation import distill_mlp
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.neural.contracts import (
    ActivationName,
    DatasetSpec,
    DistillationLossMix,
    DistillationSpec,
    NeuralModelSpec,
    NeuralTask,
    OptimizerName,
    OptimizerSpec,
    TrainingSpec,
)
from oec.neural.runtime import TrainingRuntimeSpec


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    """Distill a supplied local MLP checkpoint into a bounded student MLP."""
    try:
        dataset = DatasetSpec(
            x=inputs["x"], y=inputs["y"], val_fraction=float(inputs.get("val_fraction", 0.0))
        )
        student = NeuralModelSpec(
            input_dim=len(dataset.x[0]),
            output_dim=1,
            hidden_dims=list(inputs.get("student_hidden_dims", [8])),
            activation=ActivationName(inputs.get("activation", "relu")),
            dropout=float(inputs.get("dropout", 0.0)),
        )
        training = TrainingSpec(
            task=NeuralTask.REGRESSION,
            epochs=int(inputs.get("epochs", 80)),
            batch_size=int(inputs.get("batch_size", 16)),
            optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=float(inputs.get("lr", 0.01))),
            seed=int(inputs.get("seed", 42)),
            normalize_x=bool(inputs.get("normalize_x", True)),
        )
        policy = DistillationSpec(
            temperature=float(inputs.get("temperature", 1.0)),
            loss_mix=DistillationLossMix(inputs.get("loss_mix", "soft_and_target")),
            soft_weight=float(inputs.get("soft_weight", 0.5)),
            max_epochs=int(inputs.get("max_epochs", 100)),
            max_batch_size=int(inputs.get("max_batch_size", 128)),
        )
        if training.epochs > policy.max_epochs:
            raise ValueError("epochs exceeds max_epochs")
        if training.batch_size > policy.max_batch_size:
            raise ValueError("batch_size exceeds max_batch_size")
        runtime = TrainingRuntimeSpec(
            seed=training.seed,
            device=training.device,
            epochs=training.epochs,
            batch_size=training.batch_size,
            optimizer=training.optimizer,
            checkpoint_storage=str(inputs.get("checkpoint_storage", "json_inline")),  # type: ignore[arg-type]
        )
        result = distill_mlp(
            dataset,
            inputs["teacher_checkpoint"],
            student,
            training,
            policy,
            teacher_normalize=inputs.get("teacher_normalize"),
            runtime=runtime,
        )
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "backend": "torch", "message": exc.message},
        }
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "result": {"error": {"type": type(exc).__name__, "message": str(exc)}},
            "diagnostics": {"converged": False, "backend": "torch", "message": str(exc)},
        }
    payload = result.model_dump(mode="json")
    return {
        "result": payload,
        "diagnostics": {
            "converged": True,
            "backend": "torch",
            "seed": result.seed,
            "student_checkpoint_compatible": True,
        },
    }
