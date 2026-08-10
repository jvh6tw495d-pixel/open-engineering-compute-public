"""Transformer encoder for sequences (N4) — not an LLM."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.metrics import classification_metrics, regression_metrics
from oec.kernel.neural.runtime import (
    count_parameters,
    enforce_max_params,
    fit_minibatches,
    prepare_device_and_seeds,
    save_checkpoint,
)
from oec.kernel.neural.seeding import torch_version
from oec.neural.contracts import DeviceSpec, OptimizerName, OptimizerSpec
from oec.neural.hashing import dataset_fingerprint, model_spec_fingerprint
from oec.neural.runtime import CapacityName, TrainingRuntimeSpec


def _require_torch() -> Any:
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise TorchNotAvailableError(
            "PyTorch is not installed. Install with: uv sync --extra neural"
        ) from exc
    return torch, nn


def build_transformer_encoder(
    n_features: int,
    *,
    d_model: int = 64,
    n_heads: int = 4,
    n_layers: int = 2,
    ff_dim: int = 128,
    dropout: float = 0.1,
    output_dim: int = 1,
) -> Any:
    torch, nn = _require_torch()
    if d_model % n_heads != 0:
        raise ValueError("d_model must be divisible by n_heads")

    class TxModel(nn.Module):  # type: ignore[misc, name-defined]
        def __init__(self) -> None:
            super().__init__()
            self.input_proj = nn.Linear(n_features, d_model)
            layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=n_heads,
                dim_feedforward=ff_dim,
                dropout=dropout,
                batch_first=True,
                activation="gelu",
            )
            self.encoder = nn.TransformerEncoder(layer, num_layers=n_layers)
            self.head = nn.Linear(d_model, output_dim)

        def forward(self, x: Any) -> Any:
            h = self.input_proj(x)
            h = self.encoder(h)
            h = h.mean(dim=1)
            return self.head(h)

    return TxModel()


def train_transformer_sequence(
    x: Any,
    y: Any,
    *,
    task: Literal["regression", "classification"] = "regression",
    n_classes: int = 1,
    d_model: int = 64,
    n_heads: int = 4,
    n_layers: int = 2,
    ff_dim: int = 128,
    dropout: float = 0.1,
    epochs: int = 40,
    batch_size: int = 16,
    lr: float = 1e-3,
    seed: int = 42,
    device: str = "cpu",
    runtime: TrainingRuntimeSpec | None = None,
    capacity: CapacityName | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    torch, nn = _require_torch()
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError("x must be 3D [n, seq_len, features]")
    n, _seq, n_feat = arr.shape
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    if y_arr.shape[0] != n:
        raise ValueError("len(y) must equal n")

    out_dim = 1 if task == "regression" or n_classes == 2 else n_classes
    rt = runtime or TrainingRuntimeSpec(
        seed=seed,
        device=DeviceSpec(device=device),
        epochs=epochs,
        batch_size=batch_size,
        optimizer=OptimizerSpec(name=OptimizerName.ADAMW, lr=lr),
        early_stopping_patience=None,
    )
    resolved, det = prepare_device_and_seeds(rt)
    model = build_transformer_encoder(
        n_feat,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        ff_dim=ff_dim,
        dropout=dropout,
        output_dim=out_dim,
    ).to(resolved)
    n_params = count_parameters(model)
    enforce_max_params(n_params, rt.max_params)

    if task == "regression":
        crit: Any = nn.MSELoss()
    elif n_classes == 2:
        crit = nn.BCEWithLogitsLoss()
    else:
        crit = nn.CrossEntropyLoss()

    x_t = torch.tensor(arr, dtype=torch.float32, device=resolved)
    multiclass = task == "classification" and n_classes > 2
    if task == "regression" or n_classes == 2:
        y_t = torch.tensor(y_arr, dtype=torch.float32, device=resolved).view(-1, 1)
    else:
        y_t = torch.tensor(y_arr, dtype=torch.long, device=resolved)

    history, epochs_ran = fit_minibatches(
        model, x_t, y_t, crit, rt, device=resolved, multiclass=multiclass
    )

    model.eval()
    with torch.no_grad():
        pred = model(x_t).cpu().numpy()
    if task == "regression":
        metrics = regression_metrics(y_arr, pred.reshape(-1))
    elif n_classes == 2:
        labels = (1 / (1 + np.exp(-pred.reshape(-1))) >= 0.5).astype(int)
        metrics = classification_metrics(y_arr.astype(int), labels, 2)
    else:
        labels = np.argmax(pred, axis=1)
        metrics = classification_metrics(y_arr.astype(int), labels, n_classes)

    spec = {
        "architecture": "transformer_encoder",
        "n_features": n_feat,
        "d_model": d_model,
        "n_heads": n_heads,
        "n_layers": n_layers,
        "ff_dim": ff_dim,
        "dropout": dropout,
        "output_dim": out_dim,
        "task": task,
        "n_classes": n_classes,
    }
    meta = {
        "architecture": "transformer_encoder",
        "model_spec": spec,
        "task": f"transformer_{task}",
        "n_params": n_params,
        "capacity": capacity,
    }
    ckpt, cref = save_checkpoint(
        storage=rt.checkpoint_storage,
        state_dict=model.state_dict(),
        meta=meta,
        run_id=run_id,
    )
    return {
        "task": f"transformer_{task}",
        "backend": "torch",
        "backend_version": torch_version(),
        "device": resolved,
        "seed": rt.seed,
        "deterministic_status": det,
        "epochs_ran": epochs_ran,
        "train_metrics": metrics,
        "history": history[-5:],
        "checkpoint": ckpt,
        "checkpoint_ref": cref.model_dump(mode="json"),
        "n_train": n,
        "n_params": n_params,
        "capacity": capacity,
        "runtime": {
            "lr_scheduler": rt.lr_scheduler,
            "grad_clip": rt.grad_clip,
            "amp": rt.amp,
            "max_params": rt.max_params,
            "checkpoint_storage": rt.checkpoint_storage,
        },
        "dataset_fingerprint": dataset_fingerprint([[float(n_feat)]], y_arr.tolist()),
        "model_fingerprint": model_spec_fingerprint(spec),
    }
