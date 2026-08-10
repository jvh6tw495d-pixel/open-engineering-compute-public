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
from oec.neural.runtime import CapacityName, TrainingRuntimeSpec, resolve_mlp_hidden_dims


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    x = inputs["x"]
    y = inputs["y"]
    capacity: CapacityName | None = inputs.get("capacity")  # type: ignore[assignment]
    raw_hidden = inputs.get("hidden_dims")
    # Precedence (Part A.5): raw hidden_dims wins; else capacity; else tiny
    if raw_hidden is not None:
        hidden, capacity_used = list(raw_hidden), None
    else:
        hidden, capacity_used = resolve_mlp_hidden_dims(
            capacity=capacity or "tiny",
            hidden_dims=None,
        )

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
        dropout=float(inputs.get("dropout", 0.0)),
    )
    patience = inputs.get("early_stopping_patience", 10)
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
        early_stopping_patience=None if patience is None else int(patience),
    )
    # Prefer file checkpoint for dense/wide unless overridden
    if "checkpoint_storage" in inputs:
        storage = str(inputs["checkpoint_storage"])
    elif capacity_used in ("dense", "wide"):
        storage = "file"
    else:
        storage = "json_inline"

    runtime = TrainingRuntimeSpec(
        seed=training.seed,
        device=training.device,
        epochs=training.epochs,
        batch_size=training.batch_size,
        optimizer=training.optimizer,
        lr_scheduler=str(inputs.get("lr_scheduler", "none")),  # type: ignore[arg-type]
        step_size=int(inputs.get("step_size", 50)),
        grad_clip=inputs.get("grad_clip"),
        amp=bool(inputs.get("amp", False)),
        early_stopping_patience=training.early_stopping_patience,
        max_params=int(inputs.get("max_params", 5_000_000)),
        max_seconds=inputs.get("max_seconds"),
        checkpoint_storage=storage,  # type: ignore[arg-type]
    )
    try:
        result = train_mlp(
            dataset,
            model,
            training,
            runtime=runtime,
            capacity=capacity_used,
        )
    except TorchNotAvailableError as exc:
        return {
            "result": {"error": exc.to_dict()},
            "diagnostics": {
                "converged": False,
                "message": exc.message,
                "backend": "torch",
            },
        }
    except ValueError as exc:
        return {
            "result": {"error": {"type": "ValueError", "message": str(exc)}},
            "diagnostics": {
                "converged": False,
                "message": str(exc),
                "backend": "torch",
            },
        }

    payload = result.model_dump(mode="json")
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
            "n_params": result.n_params,
            "capacity": result.capacity,
        },
    }
