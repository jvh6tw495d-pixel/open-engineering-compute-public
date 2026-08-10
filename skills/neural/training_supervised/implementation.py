"""neural.training.supervised — unified supervised gradient entry (ADR 0033 W1)."""

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
from oec.neural.runtime import TrainingRuntimeSpec, resolve_mlp_hidden_dims


def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    x, y = inputs["x"], inputs["y"]
    raw = inputs.get("hidden_dims")
    hidden, cap = resolve_mlp_hidden_dims(
        capacity=inputs.get("capacity") or "tiny",
        hidden_dims=list(raw) if raw is not None else None,
    )
    if raw is not None:
        cap = None
    opt_name = OptimizerName(str(inputs.get("optimizer", "adam")))
    model = NeuralModelSpec(
        input_dim=len(x[0]),
        hidden_dims=list(hidden),
        activation=ActivationName(inputs.get("activation", "relu")),
        dropout=float(inputs.get("dropout", 0.0)),
    )
    patience = inputs.get("early_stopping_patience", 10)
    training = TrainingSpec(
        task=NeuralTask.REGRESSION,
        epochs=int(inputs.get("epochs", 80)),
        batch_size=int(inputs.get("batch_size", 16)),
        loss=LossName(str(inputs.get("loss", "mse"))),
        optimizer=OptimizerSpec(
            name=opt_name,
            lr=float(inputs.get("lr", 0.01)),
            weight_decay=float(inputs.get("weight_decay", 0.0)),
            momentum=float(inputs.get("momentum", 0.0)),
        ),
        seed=int(inputs.get("seed", 42)),
        device=DeviceSpec(device=inputs.get("device", "cpu")),
        normalize_x=bool(inputs.get("normalize_x", True)),
        early_stopping_patience=None if patience is None else int(patience),
    )
    runtime = TrainingRuntimeSpec(
        seed=training.seed,
        device=training.device,
        epochs=training.epochs,
        batch_size=training.batch_size,
        optimizer=training.optimizer,
        lr_scheduler=str(inputs.get("lr_scheduler", "none")),
        grad_clip=inputs.get("grad_clip"),
        early_stopping_patience=training.early_stopping_patience,
        checkpoint_storage=str(inputs.get("checkpoint_storage", "json_inline")),
    )
    try:
        result = train_mlp(
            DatasetSpec(x=x, y=y, val_fraction=float(inputs.get("val_fraction", 0.2))),
            model,
            training,
            runtime=runtime,
            capacity=cap,
        )
    except (TorchNotAvailableError, ValueError) as exc:
        msg = getattr(exc, "message", str(exc))
        return {
            "result": {"error": {"message": msg}},
            "diagnostics": {"converged": False, "backend": "torch", "message": msg},
        }
    payload = result.model_dump(mode="json")
    payload["history"] = (payload.get("history") or [])[-5:]
    return {
        "result": payload,
        "diagnostics": {
            "converged": True,
            "backend": "torch",
            "mode": "gradient",
            "seed": result.seed,
            "n_params": result.n_params,
            "capacity": result.capacity,
            "train_metrics": result.train_metrics,
        },
    }
