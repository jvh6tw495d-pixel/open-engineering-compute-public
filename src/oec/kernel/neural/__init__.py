"""Neural kernel — thin PyTorch wrappers (ADR 0031/0032, merit: PyTorch)."""

from __future__ import annotations

from oec.kernel.neural.autoencoder import train_autoencoder
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.gnn import train_gnn
from oec.kernel.neural.runtime import count_parameters, load_state_dict_from_checkpoint
from oec.kernel.neural.sequences import train_sequence_model
from oec.kernel.neural.training import evaluate_mlp, predict_mlp, train_mlp
from oec.kernel.neural.transformer import train_transformer_sequence

__all__ = [
    "TorchNotAvailableError",
    "count_parameters",
    "evaluate_mlp",
    "load_state_dict_from_checkpoint",
    "predict_mlp",
    "train_autoencoder",
    "train_gnn",
    "train_mlp",
    "train_sequence_model",
    "train_transformer_sequence",
]
