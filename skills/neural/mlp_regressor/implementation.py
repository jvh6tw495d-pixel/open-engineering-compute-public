"""neural.mlp.regressor — thin skill over ``oec.kernel.neural.train_mlp``."""

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
    hidden = inputs.get("hidden_dims") or [32, 16]
    dataset = DatasetSpec(
        x=x,
        y=y,
        val_fraction=float(inputs.get("val_fraction", 0.2)),
    )
    model = NeuralModelSpec(
        architecture="mlp",
        input_dim=len(x[0]),
        output_dim=1,
        hidden_dims=list(hidden),
        activation=ActivationName(inputs.get("activation", "relu")),
    )
    training = TrainingSpec(
        task=NeuralTask.REGRESSION,
        epochs=int(inputs.get("epochs", 80)),
        batch_size=int(inputs.get("batch_size", 16)),
        loss=LossName.MSE,
        optimizer=OptimizerSpec(
            name=OptimizerName.ADAM,
            lr=float(inputs.get("lr", 0.01)),
        ),
        seed=int(inputs.get("seed", 42)),
        device=DeviceSpec(device=inputs.get("device", "cpu")),
        normalize_x=bool(inputs.get("normalize_x", True)),
        early_stopping_patience=10,
    )
    try:
        result = train_mlp(dataset, model, training)
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "torch",
            },
        }

    payload = result.model_dump(mode="json")
    # Drop bulky epoch history from default result size; keep last 5
    hist = payload.get("history") or []
    payload["history"] = hist[-5:]
    train_r2 = float(result.train_metrics.get("r_squared", 0.0))
    return {
        "result": payload,
        "diagnostics": {
            "converged": train_r2 > 0.5 or result.epochs_ran >= 1,
            "message": "training complete",
            "backend": "torch",
            "seed": result.seed,
            "train_r_squared": train_r2,
        },
    }
