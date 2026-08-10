"""neural.mlp.classifier — multiclass MLP via cross-entropy."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import train_mlp
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
from oec.neural.runtime import CapacityName, TrainingRuntimeSpec, resolve_mlp_hidden_dims


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    x = inputs["x"]
    y = inputs["y"]
    n_classes = int(inputs.get("n_classes", 2))
    labels = [int(v) for v in y]
    if any(lab < 0 or lab >= n_classes for lab in labels):
        raise ValueError(f"y labels must be in 0..{n_classes - 1}")

    capacity_raw = inputs.get("capacity")
    capacity: CapacityName | None = capacity_raw if capacity_raw else None
    raw_hidden = inputs.get("hidden_dims")
    if raw_hidden is not None:
        hidden, capacity_used = list(raw_hidden), None
    elif capacity is not None:
        hidden, capacity_used = resolve_mlp_hidden_dims(capacity=capacity, hidden_dims=None)
    else:
        hidden, capacity_used = resolve_mlp_hidden_dims(capacity="tiny", hidden_dims=None)

    dataset = DatasetSpec(
        x=x,
        y=[float(v) for v in labels],
        val_fraction=float(inputs.get("val_fraction", 0.2)),
    )
    out_dim = 1 if n_classes == 2 else n_classes
    model = NeuralModelSpec(
        architecture="mlp",
        input_dim=len(x[0]),
        output_dim=out_dim,
        hidden_dims=list(hidden),
        activation=ActivationName(inputs.get("activation", "relu")),
    )
    task = (
        NeuralTask.BINARY_CLASSIFICATION if n_classes == 2 else NeuralTask.MULTICLASS_CLASSIFICATION
    )
    loss = LossName.BCE if n_classes == 2 else LossName.CROSS_ENTROPY

    training = TrainingSpec(
        task=task,
        epochs=int(inputs.get("epochs", 80)),
        batch_size=int(inputs.get("batch_size", 16)),
        loss=loss,
        optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=float(inputs.get("lr", 0.01))),
        seed=int(inputs.get("seed", 42)),
        device=DeviceSpec(device=inputs.get("device", "cpu")),
        normalize_x=True,
    )
    runtime = TrainingRuntimeSpec(
        seed=training.seed,
        device=training.device,
        epochs=training.epochs,
        batch_size=training.batch_size,
        optimizer=training.optimizer,
        lr_scheduler=str(inputs.get("lr_scheduler", "none")),
        grad_clip=inputs.get("grad_clip"),
        amp=bool(inputs.get("amp", False)),
        early_stopping_patience=training.early_stopping_patience,
        max_params=int(inputs.get("max_params", 5_000_000)),
        checkpoint_storage=str(inputs.get("checkpoint_storage", "json_inline")),
    )
    try:
        result = train_mlp(dataset, model, training, runtime=runtime, capacity=capacity_used)
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "backend": "torch"},
        }
    except ValueError as exc:
        return {
            "result": {"error": {"type": "ValueError", "message": str(exc)}},
            "diagnostics": {"converged": False, "message": str(exc), "backend": "torch"},
        }
    payload = result.model_dump(mode="json")
    payload["history"] = (payload.get("history") or [])[-5:]
    acc = float(result.train_metrics.get("accuracy", 0.0))
    return {
        "result": payload,
        "diagnostics": {
            "converged": acc > 0.5 or result.epochs_ran >= 1,
            "message": "training complete",
            "backend": "torch",
            "seed": result.seed,
            "train_accuracy": acc,
            "n_params": result.n_params,
            "capacity": result.capacity,
        },
    }
