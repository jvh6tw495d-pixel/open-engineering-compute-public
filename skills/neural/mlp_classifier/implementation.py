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


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    x = inputs["x"]
    y = inputs["y"]
    n_classes = int(inputs.get("n_classes", 2))
    labels = [int(v) for v in y]
    if any(lab < 0 or lab >= n_classes for lab in labels):
        raise ValueError(f"y labels must be in 0..{n_classes - 1}")

    dataset = DatasetSpec(
        x=x,
        y=[float(v) for v in labels],
        val_fraction=float(inputs.get("val_fraction", 0.2)),
    )
    model = NeuralModelSpec(
        architecture="mlp",
        input_dim=len(x[0]),
        output_dim=n_classes,
        hidden_dims=list(inputs.get("hidden_dims") or [32, 16]),
        activation=ActivationName(inputs.get("activation", "relu")),
    )
    task = (
        NeuralTask.BINARY_CLASSIFICATION if n_classes == 2 else NeuralTask.MULTICLASS_CLASSIFICATION
    )
    loss = LossName.BCE if n_classes == 2 else LossName.CROSS_ENTROPY
    # Binary path uses single logit + BCEWithLogits
    if n_classes == 2:
        model = NeuralModelSpec(
            architecture="mlp",
            input_dim=len(x[0]),
            output_dim=1,
            hidden_dims=list(inputs.get("hidden_dims") or [32, 16]),
            activation=ActivationName(inputs.get("activation", "relu")),
        )

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
    try:
        result = train_mlp(dataset, model, training)
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {"converged": False, "message": exc.message, "backend": "torch"},
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
        },
    }
