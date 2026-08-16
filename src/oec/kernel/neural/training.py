"""Supervised MLP train / eval / predict (merit: PyTorch).

Uses the shared dense runtime helpers (Part A) for optimizer, scheduler,
grad clip, AMP, param caps, and checkpoint storage.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.metrics import classification_metrics, regression_metrics
from oec.kernel.neural.mlp import build_mlp
from oec.kernel.neural.runtime import (
    TrainTimer,
    build_optimizer,
    build_scheduler,
    count_parameters,
    enforce_max_params,
    load_state_dict_from_checkpoint,
    maybe_clip_grads,
    prepare_device_and_seeds,
    require_torch,
    resolve_amp,
    save_checkpoint,
)
from oec.kernel.neural.seeding import torch_version
from oec.neural.contracts import (
    DatasetSpec,
    LossName,
    NeuralModelSpec,
    NeuralTask,
    TrainingSpec,
)
from oec.neural.hashing import dataset_fingerprint, model_spec_fingerprint
from oec.neural.results import NeuralEvaluationResult, NeuralTrainingResult
from oec.neural.runtime import (
    CapacityName,
    TrainingRuntimeSpec,
    estimate_mlp_param_count,
)


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


def runtime_from_training(training: TrainingSpec) -> TrainingRuntimeSpec:
    """Bridge legacy TrainingSpec into TrainingRuntimeSpec (shared defaults)."""
    return TrainingRuntimeSpec(
        seed=training.seed,
        device=training.device,
        epochs=training.epochs,
        batch_size=training.batch_size,
        optimizer=training.optimizer,
        early_stopping_patience=training.early_stopping_patience,
    )


def train_mlp(
    dataset: DatasetSpec,
    model_spec: NeuralModelSpec,
    training: TrainingSpec,
    *,
    runtime: TrainingRuntimeSpec | None = None,
    capacity: CapacityName | None = None,
    run_id: str | None = None,
) -> NeuralTrainingResult:
    """Train an MLP; returns metrics + checkpoint (inline JSON or file)."""
    torch = require_torch()
    rt = runtime or runtime_from_training(training)

    if model_spec.input_dim != len(dataset.x[0]):
        raise ValueError(
            f"model input_dim={model_spec.input_dim} != feature width={len(dataset.x[0])}"
        )

    # Pre-check param cap without building (fast fail for dense misconfig)
    est = estimate_mlp_param_count(
        model_spec.input_dim, list(model_spec.hidden_dims), model_spec.output_dim
    )
    enforce_max_params(est, rt.max_params)

    device, det_status = prepare_device_and_seeds(rt)
    use_amp = resolve_amp(torch, rt, device)

    x = np.asarray(dataset.x, dtype=np.float64)
    y = np.asarray(dataset.y, dtype=np.float64)

    x_train, y_train, x_val, y_val = _split(x, y, dataset.val_fraction, rt.seed)
    norm_params: dict[str, list[float]] | None = None
    if training.normalize_x:
        x_train, norm_params = _normalize_fit(x_train)
        if len(x_val):
            x_val = _normalize_apply(x_val, norm_params)

    model = build_mlp(model_spec).to(device)
    n_params = count_parameters(model)
    enforce_max_params(n_params, rt.max_params)

    criterion = _loss_fn(torch, training.loss, training.task)
    optim = build_optimizer(
        torch,
        rt.optimizer.name,
        model.parameters(),
        rt.optimizer.lr,
        rt.optimizer.weight_decay,
        momentum=rt.optimizer.momentum,
    )
    scheduler = build_scheduler(torch, optim, rt)
    scaler = None
    if use_amp:
        # torch.amp.GradScaler preferred; fall back for older torch
        try:
            scaler = torch.amp.GradScaler("cuda", enabled=True)
        except (AttributeError, TypeError):
            scaler = torch.cuda.amp.GradScaler(enabled=True)

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
    patience_left = rt.early_stopping_patience
    epochs_ran = 0
    timer = TrainTimer(rt.max_seconds)

    for epoch in range(rt.epochs):
        if timer.expired():
            break
        model.train()
        perm = torch.randperm(n, device=device)
        total_loss = 0.0
        batches = 0
        for start in range(0, n, rt.batch_size):
            idx = perm[start : start + rt.batch_size]
            xb, yb = x_t[idx], y_t[idx]
            optim.zero_grad(set_to_none=True)
            if use_amp:
                assert scaler is not None
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    out = model(xb)
                    if training.task == NeuralTask.MULTICLASS_CLASSIFICATION:
                        loss = criterion(out, yb)
                    else:
                        loss = criterion(out, yb if out.shape == yb.shape else yb.view_as(out))
                scaler.scale(loss).backward()
                if rt.grad_clip is not None:
                    scaler.unscale_(optim)
                    maybe_clip_grads(torch, model, rt.grad_clip)
                scaler.step(optim)
                scaler.update()
            else:
                out = model(xb)
                if training.task == NeuralTask.MULTICLASS_CLASSIFICATION:
                    loss = criterion(out, yb)
                else:
                    loss = criterion(out, yb if out.shape == yb.shape else yb.view_as(out))
                loss.backward()
                maybe_clip_grads(torch, model, rt.grad_clip)
                optim.step()
            total_loss += float(loss.item())
            batches += 1
        if scheduler is not None:
            scheduler.step()
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
                patience_left = rt.early_stopping_patience
            elif rt.early_stopping_patience is not None:
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

    meta = {
        "architecture": "mlp",
        "model_spec": model_spec.model_dump(mode="json"),
        "task": training.task.value,
        "n_params": n_params,
        "capacity": capacity,
        "normalize": norm_params,
        "normalize_x": training.normalize_x,
    }
    ckpt_payload, ckpt_ref = save_checkpoint(
        storage=rt.checkpoint_storage,
        state_dict=model.state_dict(),
        meta=meta,
        run_id=run_id,
    )

    runtime_meta = {
        "lr_scheduler": rt.lr_scheduler,
        "grad_clip": rt.grad_clip,
        "amp": use_amp,
        "max_params": rt.max_params,
        "max_seconds": rt.max_seconds,
        "checkpoint_storage": rt.checkpoint_storage,
        "estimated_params": est,
    }

    return NeuralTrainingResult(
        task=training.task.value,
        backend="torch",
        backend_version=torch_version(),
        device=device,
        seed=rt.seed,
        deterministic_status=det_status,
        epochs_ran=epochs_ran,
        train_metrics=train_metrics,
        val_metrics=val_metrics,
        history=history,
        checkpoint=ckpt_payload,
        normalize=norm_params,
        model_spec=model_spec.model_dump(mode="json"),
        n_train=int(x_train.shape[0]),
        n_val=int(x_val.shape[0]),
        dataset_fingerprint=dataset_fingerprint(dataset.x, dataset.y),
        model_fingerprint=model_spec_fingerprint(model_spec.model_dump(mode="json")),
        n_params=n_params,
        capacity=capacity,
        runtime=runtime_meta,
        checkpoint_ref=ckpt_ref.model_dump(mode="json"),
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
    labels = np.argmax(pred, axis=1)
    return classification_metrics(y_true.astype(int), labels, n_classes=output_dim)


class _Unset:
    __slots__ = ()

    def __repr__(self) -> str:
        return "<UNSET>"


NORMALIZE_UNSET: Any = _Unset()


def _resolve_normalize(checkpoint: dict[str, Any], normalize: Any) -> dict[str, list[float]] | None:
    """Resolve the effective normalize state for predict/evaluate.

    A checkpoint artifact is the source of truth for the normalize state used
    at training time; an explicit ``normalize`` argument overrides it. If the
    checkpoint declares ``normalize_x=True`` but carries no ``normalize``
    state (and none was supplied explicitly), predictions would be silently
    wrong, so this fails clearly instead.
    """
    if normalize is NORMALIZE_UNSET:
        if "normalize" in checkpoint:
            return checkpoint["normalize"]  # type: ignore[no-any-return]
        if checkpoint.get("normalize_x"):
            raise ValueError(
                "checkpoint requires normalize state (normalize_x=True) but none is "
                "present on the checkpoint artifact; pass normalize explicitly"
            )
        return None
    if normalize is None and checkpoint.get("normalize_x") and "normalize" not in checkpoint:
        raise ValueError(
            "checkpoint requires normalize state (normalize_x=True) but none was provided"
        )
    return normalize  # type: ignore[no-any-return]


def predict_mlp(
    x: list[list[float]],
    checkpoint: dict[str, Any],
    normalize: dict[str, list[float]] | None | Any = NORMALIZE_UNSET,
    device: str = "cpu",
) -> list[float] | list[list[float]]:
    torch = require_torch()
    from oec.kernel.neural.seeding import configure_torch_seeds

    resolved_normalize = _resolve_normalize(checkpoint, normalize)
    resolved, _ = configure_torch_seeds(0, device)
    spec = NeuralModelSpec.model_validate(checkpoint["model_spec"])
    model = build_mlp(spec).to(resolved)
    model.load_state_dict(load_state_dict_from_checkpoint(checkpoint))
    model.eval()
    arr = np.asarray(x, dtype=np.float64)
    if resolved_normalize is not None:
        arr = _normalize_apply(arr, resolved_normalize)
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
    normalize: dict[str, list[float]] | None | Any = NORMALIZE_UNSET,
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


# Re-export for callers that imported TorchNotAvailableError via training historically
__all__ = [
    "TorchNotAvailableError",
    "evaluate_mlp",
    "predict_mlp",
    "runtime_from_training",
    "train_mlp",
]
