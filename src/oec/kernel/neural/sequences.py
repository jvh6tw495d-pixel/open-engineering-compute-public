"""Sequence models: CNN1D, LSTM, GRU, TCN (N3) — merit: PyTorch."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.metrics import classification_metrics, regression_metrics
from oec.kernel.neural.seeding import (
    configure_torch_seeds,
    state_dict_to_jsonable,
    torch_version,
)
from oec.neural.hashing import dataset_fingerprint, model_spec_fingerprint

ArchName = Literal["cnn1d", "lstm", "gru", "tcn"]


def _require_torch() -> Any:
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise TorchNotAvailableError(
            "PyTorch is not installed. Install with: uv sync --extra neural"
        ) from exc
    return torch, nn


def _to_array3(x: list[Any]) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError("x must be 3D [n, seq_len, features]")
    return arr


class _TemporalBlock:
    """Factory helpers living as plain functions to keep file simple."""


def build_sequence_model(
    arch: ArchName,
    n_features: int,
    *,
    hidden: int = 32,
    n_layers: int = 1,
    output_dim: int = 1,
    kernel_size: int = 3,
    dropout: float = 0.0,
) -> Any:
    torch, nn = _require_torch()

    class SeqModel(nn.Module):  # type: ignore[misc, name-defined]
        def __init__(self) -> None:
            super().__init__()
            self.arch = arch
            if arch == "cnn1d":
                pad = kernel_size // 2
                self.conv = nn.Sequential(
                    nn.Conv1d(n_features, hidden, kernel_size, padding=pad),
                    nn.ReLU(),
                    nn.Conv1d(hidden, hidden, kernel_size, padding=pad),
                    nn.ReLU(),
                )
                self.head = nn.Linear(hidden, output_dim)
            elif arch in ("lstm", "gru"):
                rnn_cls = nn.LSTM if arch == "lstm" else nn.GRU
                self.rnn = rnn_cls(
                    n_features,
                    hidden,
                    num_layers=n_layers,
                    batch_first=True,
                    dropout=dropout if n_layers > 1 else 0.0,
                )
                self.head = nn.Linear(hidden, output_dim)
            elif arch == "tcn":
                # Dilated causal-ish stack (simplified TCN)
                layers: list[Any] = []
                in_ch = n_features
                for dil in (1, 2, 4):
                    layers.append(
                        nn.Conv1d(
                            in_ch,
                            hidden,
                            kernel_size,
                            padding=(kernel_size - 1) * dil,
                            dilation=dil,
                        )
                    )
                    layers.append(nn.ReLU())
                    if dropout > 0:
                        layers.append(nn.Dropout(dropout))
                    in_ch = hidden
                self.tcn = nn.Sequential(*layers)
                self.head = nn.Linear(hidden, output_dim)
            else:
                raise ValueError(f"unknown arch {arch}")

        def forward(self, x: Any) -> Any:
            # x: [B, T, F]
            if self.arch == "cnn1d":
                h = self.conv(x.transpose(1, 2))  # [B, C, T]
                h = h.mean(dim=-1)
                return self.head(h)
            if self.arch in ("lstm", "gru"):
                out, _ = self.rnn(x)
                return self.head(out[:, -1, :])
            # tcn
            h = self.tcn(x.transpose(1, 2))
            # trim padding overhang approximately by taking last T
            t = x.shape[1]
            h = h[:, :, -t:]
            h = h.mean(dim=-1)
            return self.head(h)

    return SeqModel()


def train_sequence_model(
    x: list[Any],
    y: list[float],
    *,
    arch: ArchName,
    task: Literal["regression", "classification"] = "regression",
    n_classes: int = 1,
    hidden: int = 32,
    n_layers: int = 1,
    epochs: int = 40,
    batch_size: int = 16,
    lr: float = 1e-3,
    seed: int = 42,
    device: str = "cpu",
    kernel_size: int = 3,
    dropout: float = 0.0,
) -> dict[str, Any]:
    torch, nn = _require_torch()
    arr = _to_array3(x)
    n, seq_len, n_feat = arr.shape
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    if y_arr.shape[0] != n:
        raise ValueError("len(y) must equal n samples")

    out_dim = 1 if task == "regression" else max(n_classes, 2)
    if task == "classification" and n_classes == 2:
        out_dim = 1  # BCE logits

    resolved, det = configure_torch_seeds(seed, device)
    model = build_sequence_model(
        arch,
        n_feat,
        hidden=hidden,
        n_layers=n_layers,
        output_dim=out_dim,
        kernel_size=kernel_size,
        dropout=dropout,
    ).to(resolved)
    optim = torch.optim.Adam(model.parameters(), lr=lr)
    if task == "regression":
        crit: Any = nn.MSELoss()
    elif n_classes == 2:
        crit = nn.BCEWithLogitsLoss()
    else:
        crit = nn.CrossEntropyLoss()

    x_t = torch.tensor(arr, dtype=torch.float32, device=resolved)
    if task == "regression" or n_classes == 2:
        y_t = torch.tensor(y_arr, dtype=torch.float32, device=resolved).view(-1, 1)
    else:
        y_t = torch.tensor(y_arr, dtype=torch.long, device=resolved)

    history: list[dict[str, float]] = []
    model.train()
    for epoch in range(epochs):
        perm = torch.randperm(n, device=resolved)
        total = 0.0
        batches = 0
        for start in range(0, n, batch_size):
            idx = perm[start : start + batch_size]
            optim.zero_grad(set_to_none=True)
            pred = model(x_t[idx])
            if task == "classification" and n_classes > 2:
                loss = crit(pred, y_t[idx])
            else:
                target = y_t[idx]
                if pred.shape != target.shape:
                    target = target.view_as(pred)
                loss = crit(pred, target)
            loss.backward()
            optim.step()
            total += float(loss.item())
            batches += 1
        history.append({"epoch": float(epoch + 1), "train_loss": total / max(batches, 1)})

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
        "architecture": arch,
        "n_features": n_feat,
        "seq_len": seq_len,
        "hidden": hidden,
        "n_layers": n_layers,
        "output_dim": out_dim,
        "kernel_size": kernel_size,
        "dropout": dropout,
        "task": task,
        "n_classes": n_classes,
    }
    return {
        "task": f"sequence_{task}",
        "backend": "torch",
        "backend_version": torch_version(),
        "device": resolved,
        "seed": seed,
        "deterministic_status": det,
        "epochs_ran": epochs,
        "train_metrics": metrics,
        "history": history[-5:],
        "checkpoint": {
            "architecture": arch,
            "model_spec": spec,
            "state_dict": state_dict_to_jsonable(model.state_dict()),
            "task": f"sequence_{task}",
        },
        "n_train": n,
        "dataset_fingerprint": dataset_fingerprint(
            [[float(seq_len), float(n_feat)]], y_arr.tolist()
        ),
        "model_fingerprint": model_spec_fingerprint(spec),
        "arch": arch,
    }
