"""Supervised MLP train / eval / predict (merit: PyTorch)."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.metrics import classification_metrics, regression_metrics
from oec.kernel.neural.mlp import build_mlp
from oec.kernel.neural.seeding import (
    configure_torch_seeds,
    state_dict_from_jsonable,
    state_dict_to_jsonable,
    torch_version,
)
from oec.neural.contracts import (
    DatasetSpec,
    LossName,
    NeuralModelSpec,
    NeuralTask,
    OptimizerName,
    TrainingSpec,
)
from oec.neural.hashing import dataset_fingerprint, model_spec_fingerprint
from oec.neural.results import NeuralEvaluationResult, NeuralTrainingResult


def _require_torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise TorchNotAvailableError(
            "PyTorch is not installed. Install with: uv sync --extra neural"
        ) from exc
    return torch


def _loss_fn(torch: Any, name: LossName, task: NeuralTask) -> Any:
    if task == NeuralTask.REGRESSION:
        mapping = {
            LossName.MSE: torch.nn.MSELoss(),
            LossName.MAE: torch.nn.L1Loss(),
            LossName.HUBER: torch.nn.SmoothL1Loss(),
        }
        if name not in mapping:
            raise ValueError(f"loss {name} is not valid for regression")
        return mapping[name]
    if name == LossName.BCE:
        return torch.nn.BCEWithLogitsLoss()
    if name == LossName.CROSS_ENTROPY:
        return torch.nn.CrossEntropyLoss()
    raise ValueError(f"loss {name} is not valid for classification")


def _optimizer(torch: Any, name: OptimizerName, params: Any, lr: float, weight_decay: float) -> Any:
    if name == OptimizerName.ADAM:
        return torch.optim.Adam(params, lr=lr, weight_decay=weight_decay)
    if name == OptimizerName.ADAMW:
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)
    if name == OptimizerName.SGD:
        return torch.optim.SGD(params, lr=lr, weight_decay=weight_decay)
    raise ValueError(f"unknown optimizer {name}")


def _split(
    x: np.ndarray, y: np.ndarray, val_fraction: float, seed: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = x.shape[0]
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_val = int(round(n * val_fraction)) if val_fraction > 0 else 0
    if n_val > 0 and n_val < n:
        val_idx, train_idx = idx[:n_val], idx[n_val:]
    else:
        train_idx, val_idx = idx, np.array([], dtype=int)
    return x[train_idx], y[train_idx], x[val_idx], y[val_idx]


def _normalize_fit(x: np.ndarray) -> tuple[np.ndarray, dict[str, list[float]]]:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std = np.where(std < 1e-12, 1.0, std)
    return (x - mean) / std, {"mean": mean.tolist(), "std": std.tolist()}


def _normalize_apply(x: np.ndarray, params: dict[str, list[float]]) -> np.ndarray:
    mean = np.asarray(params["mean"], dtype=float)
    std = np.asarray(params["std"], dtype=float)
    out = (x - mean) / std
    return np.asarray(out, dtype=float)


def train_mlp(
    dataset: DatasetSpec,
    model_spec: NeuralModelSpec,
    training: TrainingSpec,
) -> NeuralTrainingResult:
    """Train an MLP; returns metrics + JSON-serializable checkpoint."""
    torch = _require_torch()

    if model_spec.input_dim != len(dataset.x[0]):
        raise ValueError(
            f"model input_dim={model_spec.input_dim} != feature width={len(dataset.x[0])}"
        )

    device, det_status = configure_torch_seeds(training.seed, training.device.device)
    x = np.asarray(dataset.x, dtype=np.float64)
    y = np.asarray(dataset.y, dtype=np.float64)

    x_train, y_train, x_val, y_val = _split(x, y, dataset.val_fraction, training.seed)
    norm_params: dict[str, list[float]] | None = None
    if training.normalize_x:
        x_train, norm_params = _normalize_fit(x_train)
        if len(x_val):
            x_val = _normalize_apply(x_val, norm_params)

    model = build_mlp(model_spec).to(device)
    criterion = _loss_fn(torch, training.loss, training.task)
    optim = _optimizer(
        torch,
        training.optimizer.name,
        model.parameters(),
        training.optimizer.lr,
        training.optimizer.weight_decay,
    )

    x_t = torch.tensor(x_train, dtype=torch.float32, device=device)
    if training.task == NeuralTask.REGRESSION:
        y_t = torch.tensor(y_train, dtype=torch.float32, device=device).view(-1, 1)
        if model_spec.output_dim != 1:
            raise ValueError("regression expects output_dim=1 in N1")
    elif training.task == NeuralTask.BINARY_CLASSIFICATION:
        y_t = torch.tensor(y_train, dtype=torch.float32, device=device).view(-1, 1)
    else:
        y_t = torch.tensor(y_train, dtype=torch.long, device=device)

    n = x_t.shape[0]
    history: list[dict[str, float]] = []
    best_state = None
    best_val = float("inf")
    patience_left = training.early_stopping_patience
    epochs_ran = 0

    for epoch in range(training.epochs):
        model.train()
        perm = torch.randperm(n, device=device)
        total_loss = 0.0
        batches = 0
        for start in range(0, n, training.batch_size):
            idx = perm[start : start + training.batch_size]
            xb, yb = x_t[idx], y_t[idx]
            optim.zero_grad(set_to_none=True)
            out = model(xb)
            if training.task == NeuralTask.MULTICLASS_CLASSIFICATION:
                loss = criterion(out, yb)
            else:
                loss = criterion(out, yb if out.shape == yb.shape else yb.view_as(out))
            loss.backward()
            optim.step()
            total_loss += float(loss.item())
            batches += 1
        epochs_ran = epoch + 1
        train_loss = total_loss / max(batches, 1)
        entry: dict[str, float] = {"epoch": float(epochs_ran), "train_loss": train_loss}

        if len(x_val):
            model.eval()
            with torch.no_grad():
                xv = torch.tensor(x_val, dtype=torch.float32, device=device)
                pred = model(xv)
                if training.task in (
                    NeuralTask.REGRESSION,
                    NeuralTask.BINARY_CLASSIFICATION,
                ):
                    yv = torch.tensor(y_val, dtype=torch.float32, device=device).view(-1, 1)
                    val_loss = float(criterion(pred, yv).item())
                else:
                    yv = torch.tensor(y_val, dtype=torch.long, device=device)
                    val_loss = float(criterion(pred, yv).item())
            entry["val_loss"] = val_loss
            if val_loss < best_val - 1e-12:
                best_val = val_loss
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                patience_left = training.early_stopping_patience
            elif training.early_stopping_patience is not None:
                patience_left = (patience_left or 0) - 1
                if patience_left <= 0:
                    history.append(entry)
                    break
        history.append(entry)

    if best_state is not None:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        pred_train = model(x_t).detach().cpu().numpy()
    train_metrics = _metrics_for_task(training.task, y_train, pred_train, model_spec.output_dim)

    val_metrics: dict[str, float] | None = None
    if len(x_val):
        with torch.no_grad():
            xv = torch.tensor(x_val, dtype=torch.float32, device=device)
            pred_val = model(xv).detach().cpu().numpy()
        val_metrics = _metrics_for_task(training.task, y_val, pred_val, model_spec.output_dim)

    return NeuralTrainingResult(
        task=training.task.value,
        backend="torch",
        backend_version=torch_version(),
        device=device,
        seed=training.seed,
        deterministic_status=det_status,
        epochs_ran=epochs_ran,
        train_metrics=train_metrics,
        val_metrics=val_metrics,
        history=history,
        checkpoint={
            "architecture": "mlp",
            "model_spec": model_spec.model_dump(mode="json"),
            "state_dict": state_dict_to_jsonable(model.state_dict()),
            "task": training.task.value,
        },
        normalize=norm_params,
        model_spec=model_spec.model_dump(mode="json"),
        n_train=int(x_train.shape[0]),
        n_val=int(x_val.shape[0]),
        dataset_fingerprint=dataset_fingerprint(dataset.x, dataset.y),
        model_fingerprint=model_spec_fingerprint(model_spec.model_dump(mode="json")),
    )


def _metrics_for_task(
    task: NeuralTask, y_true: np.ndarray, pred: np.ndarray, output_dim: int
) -> dict[str, float]:
    if task == NeuralTask.REGRESSION:
        return regression_metrics(y_true, pred.reshape(-1))
    if task == NeuralTask.BINARY_CLASSIFICATION:
        logits = pred.reshape(-1)
        labels = (1 / (1 + np.exp(-logits)) >= 0.5).astype(int)
        return classification_metrics(y_true.astype(int), labels, n_classes=2)
    # multiclass — pred shape [n, C]
    labels = np.argmax(pred, axis=1)
    return classification_metrics(y_true.astype(int), labels, n_classes=output_dim)


def predict_mlp(
    x: list[list[float]],
    checkpoint: dict[str, Any],
    normalize: dict[str, list[float]] | None = None,
    device: str = "cpu",
) -> list[float] | list[list[float]]:
    torch = _require_torch()
    resolved, _ = configure_torch_seeds(0, device)
    spec = NeuralModelSpec.model_validate(checkpoint["model_spec"])
    model = build_mlp(spec).to(resolved)
    model.load_state_dict(state_dict_from_jsonable(checkpoint["state_dict"]))
    model.eval()
    arr = np.asarray(x, dtype=np.float64)
    if normalize is not None:
        arr = _normalize_apply(arr, normalize)
    with torch.no_grad():
        out = model(torch.tensor(arr, dtype=torch.float32, device=resolved)).cpu().numpy()
    if out.shape[1] == 1:
        return [float(v) for v in out.reshape(-1).tolist()]
    return [[float(v) for v in row] for row in out.tolist()]


def evaluate_mlp(
    x: list[list[float]],
    y: list[float],
    checkpoint: dict[str, Any],
    task: NeuralTask,
    normalize: dict[str, list[float]] | None = None,
    device: str = "cpu",
) -> NeuralEvaluationResult:
    preds = predict_mlp(x, checkpoint, normalize=normalize, device=device)
    pred_arr = np.asarray(preds, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    output_dim = int(checkpoint["model_spec"].get("output_dim", 1))
    shaped = pred_arr if pred_arr.ndim > 1 else pred_arr.reshape(-1, 1)
    metrics = _metrics_for_task(task, y_arr, shaped, output_dim)
    return NeuralEvaluationResult(
        task=task.value,
        backend="torch",
        backend_version=torch_version(),
        device=device if device != "auto" else "cpu",
        metrics=metrics,
        n=len(y),
        dataset_fingerprint=dataset_fingerprint(x, y),
        predictions=preds if isinstance(preds, list) else list(preds),
    )
