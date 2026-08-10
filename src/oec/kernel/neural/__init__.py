"""Neural kernel — thin PyTorch wrappers (ADR 0031, merit: PyTorch)."""

from __future__ import annotations

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import evaluate_mlp, predict_mlp, train_mlp

__all__ = [
    "TorchNotAvailableError",
    "evaluate_mlp",
    "predict_mlp",
    "train_mlp",
]
