"""Seed helpers for neural runs."""

from __future__ import annotations

import contextlib
from typing import Any, Literal


def configure_torch_seeds(
    seed: int, device: str
) -> tuple[str, Literal["strict", "practical", "best_effort"]]:
    """Seed RNGs and return ``(resolved_device, deterministic_status)``."""
    try:
        import torch
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("torch not available") from exc

    import numpy as np

    np.random.seed(seed)
    torch.manual_seed(seed)
    resolved = device
    if device == "auto":
        resolved = "cuda" if torch.cuda.is_available() else "cpu"
    if resolved == "cuda" and not torch.cuda.is_available():
        resolved = "cpu"

    status: Literal["strict", "practical", "best_effort"]
    if resolved == "cpu":
        with contextlib.suppress(Exception):
            torch.use_deterministic_algorithms(True)
        status = "strict"
    else:
        torch.cuda.manual_seed_all(seed)
        status = "practical"
    return resolved, status


def torch_version() -> str | None:
    try:
        import importlib.metadata

        return importlib.metadata.version("torch")
    except Exception:  # noqa: BLE001
        return None


def state_dict_to_jsonable(state: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, tensor in state.items():
        out[key] = tensor.detach().cpu().tolist()
    return out


def state_dict_from_jsonable(payload: dict[str, Any]) -> dict[str, Any]:
    import torch

    return {key: torch.tensor(value) for key, value in payload.items()}
