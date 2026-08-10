"""Shared neural train runtime helpers (Part A / N-D1).

Merit owner remains PyTorch. Family builders supply modules; this module owns
device/AMP/seed, optimizer, scheduler, grad clip, param caps, and checkpoint
file storage.
"""

from __future__ import annotations

import hashlib
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
) -> Any:
    if name == OptimizerName.ADAM:
        return torch.optim.Adam(params, lr=lr, weight_decay=weight_decay)
    if name == OptimizerName.ADAMW:
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)
    if name == OptimizerName.SGD:
        return torch.optim.SGD(params, lr=lr, weight_decay=weight_decay)
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


def checkpoint_cache_dir(run_id: str | None = None) -> Path:
    base = os.environ.get("OEC_CACHE_DIR")
    root = Path(base) if base else Path.home() / ".cache" / "oec" / "checkpoints"
    path = root / run_id if run_id else root / "anonymous"
    path.mkdir(parents=True, exist_ok=True)
    return path


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
        payload = {
            **meta,
            "state_dict": state_dict_to_jsonable(state_dict),
            "storage": "json_inline",
        }
        ref = CheckpointRef(storage="json_inline", format_version=1)
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
    """Load state_dict from json_inline or file checkpoint payload."""
    from oec.kernel.neural.seeding import state_dict_from_jsonable

    storage = checkpoint.get("storage", "json_inline")
    if storage == "file":
        torch = require_torch()
        path = checkpoint.get("path")
        if not path:
            raise ValueError("file checkpoint missing path")
        # weights_only=False: we store a dict with meta + state_dict (trusted local cache)
        try:
            blob = torch.load(path, map_location="cpu", weights_only=False)
        except TypeError:
            blob = torch.load(path, map_location="cpu")
        if isinstance(blob, dict) and "state_dict" in blob:
            sd = blob["state_dict"]
            if isinstance(sd, dict):
                return sd
        if isinstance(blob, dict):
            return dict(blob)
        raise ValueError("unrecognized checkpoint file format")

    # json_inline and legacy checkpoints (no storage key, embedded state_dict)
    if "state_dict" in checkpoint:
        return state_dict_from_jsonable(checkpoint["state_dict"])
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
            return np.load(p / "x.npy"), np.load(p / "y.npy")
        if p.suffix == ".npz":
            data = np.load(p)
            return data["x"], data["y"]
        # stem: path_x.npy style not used; treat as directory name
        raise ValueError("npy path must be a directory with x.npy/y.npy or a .npz file")
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
