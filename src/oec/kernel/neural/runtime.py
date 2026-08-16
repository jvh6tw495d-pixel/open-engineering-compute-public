"""Shared neural train runtime helpers (Part A / N-D1).

Merit owner remains PyTorch. Family builders supply modules; this module owns
device/AMP/seed, optimizer, scheduler, grad clip, param caps, and checkpoint
file storage.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.seeding import configure_torch_seeds, state_dict_to_jsonable
from oec.neural.contracts import OptimizerName
from oec.neural.runtime import CheckpointRef, TrainingRuntimeSpec


def require_torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise TorchNotAvailableError(
            "PyTorch is not installed. Install with: uv sync --extra neural"
        ) from exc
    return torch


def count_parameters(module: Any) -> int:
    return int(sum(p.numel() for p in module.parameters()))


def enforce_max_params(n_params: int, max_params: int) -> None:
    if n_params > max_params:
        raise ValueError(
            f"model has {n_params} parameters, exceeds max_params={max_params} "
            "(raise max_params or choose a smaller capacity)"
        )


def build_optimizer(
    torch: Any,
    name: OptimizerName,
    params: Any,
    lr: float,
    weight_decay: float,
    *,
    momentum: float = 0.0,
) -> Any:
    if name == OptimizerName.ADAM:
        return torch.optim.Adam(params, lr=lr, weight_decay=weight_decay)
    if name == OptimizerName.ADAMW:
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)
    if name == OptimizerName.SGD:
        return torch.optim.SGD(params, lr=lr, weight_decay=weight_decay, momentum=momentum)
    if name == OptimizerName.RMSPROP:
        return torch.optim.RMSprop(params, lr=lr, weight_decay=weight_decay, momentum=momentum)
    if name == OptimizerName.LBFGS:
        return torch.optim.LBFGS(params, lr=lr, max_iter=20)
    raise ValueError(f"unknown optimizer {name}")


def build_scheduler(torch: Any, optim: Any, runtime: TrainingRuntimeSpec) -> Any | None:
    if runtime.lr_scheduler == "none":
        return None
    if runtime.lr_scheduler == "cosine":
        return torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=max(runtime.epochs, 1))
    if runtime.lr_scheduler == "step":
        return torch.optim.lr_scheduler.StepLR(optim, step_size=runtime.step_size, gamma=0.5)
    raise ValueError(f"unknown lr_scheduler {runtime.lr_scheduler}")


def resolve_amp(torch: Any, runtime: TrainingRuntimeSpec, device: str) -> bool:
    """Return whether AMP should be active; raise if amp requested without CUDA."""
    if not runtime.amp:
        return False
    if device != "cuda" or not torch.cuda.is_available():
        raise ValueError(f"amp=True requires a CUDA device (got device={device!r})")
    return True


def maybe_clip_grads(torch: Any, module: Any, grad_clip: float | None) -> None:
    if grad_clip is not None:
        torch.nn.utils.clip_grad_norm_(module.parameters(), grad_clip)


def checkpoint_cache_root() -> Path:
    base = os.environ.get("OEC_CACHE_DIR")
    return Path(base) if base else Path.home() / ".cache" / "oec" / "checkpoints"


def checkpoint_cache_dir(run_id: str | None = None) -> Path:
    root = checkpoint_cache_root()
    path = root / run_id if run_id else root / "anonymous"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _canonical_json_inline_state_dict(state_dict: dict[str, Any]) -> bytes:
    """Return the exact JSON representation covered by inline checkpoint SHA-256."""
    return json.dumps(state_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")


def save_checkpoint(
    *,
    storage: str,
    state_dict: dict[str, Any],
    meta: dict[str, Any],
    run_id: str | None = None,
    filename: str = "model.pt",
) -> tuple[dict[str, Any], CheckpointRef]:
    """Persist weights; return (checkpoint_payload, CheckpointRef).

    ``json_inline`` embeds state_dict as lists (current skill default).
    ``file`` writes a torch file under OEC_CACHE_DIR and returns sha256.
    """
    torch = require_torch()
    if storage == "json_inline":
        json_state_dict = state_dict_to_jsonable(state_dict)
        canonical = _canonical_json_inline_state_dict(json_state_dict)
        payload = {
            **meta,
            "checkpoint_format_version": 1,
            "state_dict": json_state_dict,
            "sha256": hashlib.sha256(canonical).hexdigest(),
            "storage": "json_inline",
        }
        ref = CheckpointRef(storage="json_inline", sha256=payload["sha256"], format_version=1)
        return payload, ref

    if storage != "file":
        raise ValueError(f"unknown checkpoint storage {storage!r}")

    directory = checkpoint_cache_dir(run_id)
    path = directory / filename
    # Save tensors + JSON meta sidecar
    torch.save({"state_dict": state_dict, "meta": meta}, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {
        **meta,
        "checkpoint_format_version": 1,
        "storage": "file",
        "path": str(path),
        "sha256": digest,
    }
    ref = CheckpointRef(
        storage="file",
        path=str(path),
        sha256=digest,
        format_version=1,
    )
    return payload, ref


def load_state_dict_from_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    """Load state_dict from json_inline or file checkpoint payload.

    File checkpoints are untrusted public input: a sha256 digest is
    mandatory and verified against the on-disk bytes, the resolved path
    must be confined to the OEC checkpoint cache root, and the file is
    loaded with ``weights_only=True`` -- there is no unsafe fallback.
    """
    from oec.kernel.neural.seeding import state_dict_from_jsonable

    storage = checkpoint.get("storage", "json_inline")
    if storage == "file":
        torch = require_torch()
        raw_path = checkpoint.get("path")
        if not raw_path:
            raise ValueError("file checkpoint missing path")
        digest = checkpoint.get("sha256")
        if not digest:
            raise ValueError("file checkpoint missing required sha256 digest")

        path = Path(raw_path).resolve()
        root = checkpoint_cache_root().resolve()
        if not path.is_relative_to(root):
            raise ValueError(
                f"checkpoint path {path} is outside the OEC checkpoint cache root "
                f"{root}; refusing to load an unconfined file path"
            )
        if not path.is_file():
            raise ValueError(f"checkpoint file not found: {path}")

        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if not hmac.compare_digest(actual, digest):
            raise ValueError(f"checkpoint sha256 digest mismatch: expected {digest}, got {actual}")

        try:
            blob = torch.load(path, map_location="cpu", weights_only=True)
        except TypeError as exc:
            raise ValueError(
                "installed torch version does not support weights_only=True safe "
                "loading; upgrade torch to load file checkpoints"
            ) from exc
        if isinstance(blob, dict) and "state_dict" in blob and isinstance(blob["state_dict"], dict):
            return blob["state_dict"]
        raise ValueError("unrecognized/malformed checkpoint file: missing state_dict envelope")

    # Versioned inline checkpoints are public artifacts with a mandatory,
    # self-consistency digest.  The pre-versioned contract had no ``storage``
    # or ``checkpoint_format_version`` fields, so retain only that unambiguous
    # shape as a legacy compatibility path.
    if "state_dict" in checkpoint:
        state_dict = checkpoint["state_dict"]
        if not isinstance(state_dict, dict):
            raise ValueError("json_inline checkpoint state_dict must be a mapping")
        is_versioned_inline = "storage" in checkpoint or "checkpoint_format_version" in checkpoint
        if is_versioned_inline:
            if checkpoint.get("checkpoint_format_version") != 1:
                raise ValueError("json_inline checkpoint requires checkpoint_format_version=1")
            expected = checkpoint.get("sha256")
            if not isinstance(expected, str) or len(expected) != 64:
                raise ValueError("json_inline checkpoint missing required sha256 digest")
            actual = hashlib.sha256(_canonical_json_inline_state_dict(state_dict)).hexdigest()
            if not hmac.compare_digest(actual, expected):
                raise ValueError("json_inline checkpoint sha256 digest mismatch")
        return state_dict_from_jsonable(state_dict)
    raise ValueError("checkpoint has neither state_dict nor file path")


def load_dataset_arrays(
    *,
    x: list[Any] | None,
    y: list[Any] | None,
    path: str | None = None,
    fmt: str = "json_inline",
) -> tuple[Any, Any]:
    """Load (x, y) numpy arrays from inline data or npy path.

    For ``npy``, ``path`` points to a directory or stem containing ``x.npy``
    and ``y.npy``, or a single ``.npz`` with keys ``x`` and ``y``.
    Parquet support is deferred (path must be npy for N-D3 minimal).
    """
    import numpy as np

    if fmt == "json_inline":
        if x is None or y is None:
            raise ValueError("json_inline requires x and y")
        return np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)

    if not path:
        raise ValueError(f"format={fmt!r} requires path")
    p = Path(path)
    if fmt == "npy":
        if p.is_dir():
            x_arr = np.load(p / "x.npy")
            y_path = p / "y.npy"
            if y_path.exists():
                y_arr = np.load(y_path)
            else:
                # unsupervised (autoencoder): dummy y
                y_arr = np.zeros(x_arr.shape[0], dtype=np.float64)
            return x_arr, y_arr
        if p.suffix == ".npz":
            data = np.load(p)
            x_arr = data["x"]
            y_arr = data["y"] if "y" in data.files else np.zeros(x_arr.shape[0], dtype=np.float64)
            return x_arr, y_arr
        raise ValueError("npy path must be a directory with x.npy[/y.npy] or a .npz file")
    if fmt == "parquet":
        raise ValueError("parquet DatasetRef is not enabled in this slice; use npy or json_inline")
    raise ValueError(f"unknown dataset format {fmt!r}")


class TrainTimer:
    """Wall-clock budget helper for max_seconds."""

    def __init__(self, max_seconds: float | None) -> None:
        self.max_seconds = max_seconds
        self.t0 = time.perf_counter()

    def expired(self) -> bool:
        if self.max_seconds is None:
            return False
        return (time.perf_counter() - self.t0) >= self.max_seconds


def prepare_device_and_seeds(runtime: TrainingRuntimeSpec) -> tuple[str, str]:
    """Return (resolved_device, deterministic_status)."""
    require_torch()
    device, det = configure_torch_seeds(runtime.seed, runtime.device.device)
    return device, det


def dump_runtime_meta(
    runtime: TrainingRuntimeSpec, *, n_params: int, capacity: str | None
) -> dict[str, Any]:
    return {
        "lr_scheduler": runtime.lr_scheduler,
        "grad_clip": runtime.grad_clip,
        "amp": runtime.amp,
        "max_params": runtime.max_params,
        "max_seconds": runtime.max_seconds,
        "checkpoint_storage": runtime.checkpoint_storage,
        "n_params": n_params,
        "capacity": capacity,
    }


def write_sidecar_meta(path: Path, meta: dict[str, Any]) -> None:
    sidecar = path.with_suffix(path.suffix + ".meta.json")
    sidecar.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")


def make_grad_scaler(torch: Any, use_amp: bool) -> Any | None:
    if not use_amp:
        return None
    try:
        return torch.amp.GradScaler("cuda", enabled=True)
    except (AttributeError, TypeError):
        return torch.cuda.amp.GradScaler(enabled=True)


def runtime_from_skill_inputs(
    inputs: dict[str, Any],
    *,
    default_epochs: int = 40,
    default_batch_size: int = 16,
    default_lr: float = 1e-3,
    default_optimizer: str = "adam",
    default_checkpoint: str = "json_inline",
) -> TrainingRuntimeSpec:
    """Build TrainingRuntimeSpec from a skill input dict (Part A skills)."""
    from oec.neural.contracts import DeviceSpec, OptimizerName, OptimizerSpec

    opt_name = str(inputs.get("optimizer", default_optimizer)).lower()
    try:
        oname = OptimizerName(opt_name)
    except ValueError:
        oname = OptimizerName.ADAM
    storage = str(inputs.get("checkpoint_storage", default_checkpoint))
    capacity = inputs.get("capacity")
    if (
        storage == "json_inline"
        and capacity in ("dense", "wide")
        and "checkpoint_storage" not in inputs
    ):
        storage = "file"
    patience = inputs.get("early_stopping_patience", 20)
    return TrainingRuntimeSpec(
        seed=int(inputs.get("seed", 42)),
        device=DeviceSpec(device=inputs.get("device", "cpu")),
        epochs=int(inputs.get("epochs", default_epochs)),
        batch_size=int(inputs.get("batch_size", default_batch_size)),
        optimizer=OptimizerSpec(
            name=oname,
            lr=float(inputs.get("lr", default_lr)),
            weight_decay=float(inputs.get("weight_decay", 0.0)),
        ),
        lr_scheduler=str(inputs.get("lr_scheduler", "none")),
        step_size=int(inputs.get("step_size", 50)),
        grad_clip=inputs.get("grad_clip"),
        amp=bool(inputs.get("amp", False)),
        early_stopping_patience=None if patience is None else int(patience),
        max_params=int(inputs.get("max_params", 5_000_000)),
        max_seconds=inputs.get("max_seconds"),
        checkpoint_storage=storage,
    )


def load_xy_from_inputs(inputs: dict[str, Any]) -> tuple[Any, Any]:
    """Load x,y from inline arrays or DatasetRef-style path fields (N-D3)."""
    fmt = str(inputs.get("dataset_format", "json_inline"))
    path = inputs.get("dataset_path")
    if fmt == "json_inline" and path is None:
        if "x" not in inputs or "y" not in inputs:
            raise ValueError("inline dataset requires x and y")
        return load_dataset_arrays(x=inputs["x"], y=inputs["y"], fmt="json_inline")
    return load_dataset_arrays(
        x=inputs.get("x"),
        y=inputs.get("y"),
        path=path,
        fmt=fmt,
    )


def fit_minibatches(
    model: Any,
    x_t: Any,
    y_t: Any,
    criterion: Any,
    runtime: TrainingRuntimeSpec,
    *,
    device: str,
    multiclass: bool = False,
    input_transform: Any | None = None,
) -> tuple[list[dict[str, float]], int]:
    """Shared minibatch supervised loop (sequences, transformer, AE via transform).

    ``input_transform`` if set: ``inp, target = input_transform(xb, yb)``.
    """
    torch = require_torch()
    use_amp = resolve_amp(torch, runtime, device)
    optim = build_optimizer(
        torch,
        runtime.optimizer.name,
        model.parameters(),
        runtime.optimizer.lr,
        runtime.optimizer.weight_decay,
        momentum=runtime.optimizer.momentum,
    )
    scheduler = build_scheduler(torch, optim, runtime)
    scaler = make_grad_scaler(torch, use_amp)
    n = x_t.shape[0]
    history: list[dict[str, float]] = []
    timer = TrainTimer(runtime.max_seconds)
    epochs_ran = 0
    use_lbfgs = runtime.optimizer.name.value == "lbfgs"
    model.train()
    for epoch in range(runtime.epochs):
        if timer.expired():
            break
        if use_lbfgs:
            # Full-batch LBFGS closure
            def _closure() -> Any:
                optim.zero_grad(set_to_none=True)
                pred = model(x_t)
                if multiclass:
                    loss = criterion(pred, y_t)
                else:
                    loss = criterion(pred, y_t if pred.shape == y_t.shape else y_t.view_as(pred))
                loss.backward()
                return loss

            loss = optim.step(_closure)
            total = float(loss.item()) if loss is not None else 0.0
            batches = 1
        else:
            perm = torch.randperm(n, device=device)
            total = 0.0
            batches = 0
            for start in range(0, n, runtime.batch_size):
                idx = perm[start : start + runtime.batch_size]
                xb, yb = x_t[idx], y_t[idx]
                if input_transform is not None:
                    xb, yb = input_transform(xb, yb)
                optim.zero_grad(set_to_none=True)
                if use_amp:
                    assert scaler is not None
                    with torch.autocast(device_type="cuda", dtype=torch.float16):
                        pred = model(xb)
                        if multiclass:
                            loss = criterion(pred, yb)
                        else:
                            loss = criterion(
                                pred, yb if pred.shape == yb.shape else yb.view_as(pred)
                            )
                    scaler.scale(loss).backward()
                    if runtime.grad_clip is not None:
                        scaler.unscale_(optim)
                        maybe_clip_grads(torch, model, runtime.grad_clip)
                    scaler.step(optim)
                    scaler.update()
                else:
                    pred = model(xb)
                    if multiclass:
                        loss = criterion(pred, yb)
                    else:
                        loss = criterion(pred, yb if pred.shape == yb.shape else yb.view_as(pred))
                    loss.backward()
                    maybe_clip_grads(torch, model, runtime.grad_clip)
                    optim.step()
                total += float(loss.item())
                batches += 1
        if scheduler is not None and not use_lbfgs:
            scheduler.step()
        epochs_ran = epoch + 1
        history.append({"epoch": float(epochs_ran), "train_loss": total / max(batches, 1)})
    return history, epochs_ran


def fit_fullbatch(
    model: Any,
    forward_fn: Any,
    criterion: Any,
    runtime: TrainingRuntimeSpec,
    *,
    device: str,
) -> tuple[list[dict[str, float]], int]:
    """Full-batch loop (GNN node tasks). ``forward_fn()`` returns loss tensor."""
    torch = require_torch()
    use_amp = resolve_amp(torch, runtime, device)
    optim = build_optimizer(
        torch,
        runtime.optimizer.name,
        model.parameters(),
        runtime.optimizer.lr,
        runtime.optimizer.weight_decay,
        momentum=runtime.optimizer.momentum,
    )
    scheduler = build_scheduler(torch, optim, runtime)
    scaler = make_grad_scaler(torch, use_amp)
    history: list[dict[str, float]] = []
    timer = TrainTimer(runtime.max_seconds)
    epochs_ran = 0
    model.train()
    for epoch in range(runtime.epochs):
        if timer.expired():
            break
        optim.zero_grad(set_to_none=True)
        if use_amp:
            assert scaler is not None
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                loss = forward_fn()
            scaler.scale(loss).backward()
            if runtime.grad_clip is not None:
                scaler.unscale_(optim)
                maybe_clip_grads(torch, model, runtime.grad_clip)
            scaler.step(optim)
            scaler.update()
        else:
            loss = forward_fn()
            loss.backward()
            maybe_clip_grads(torch, model, runtime.grad_clip)
            optim.step()
        if scheduler is not None:
            scheduler.step()
        epochs_ran = epoch + 1
        history.append({"epoch": float(epochs_ran), "train_loss": float(loss.item())})
    return history, epochs_ran
