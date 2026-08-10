"""MLP factory — closed architecture enum only."""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.neural.contracts import ActivationName, NeuralModelSpec


def _require_torch() -> Any:
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise TorchNotAvailableError(
            "PyTorch is not installed. Install with: uv sync --extra neural"
        ) from exc
    return torch, nn


def _activation(nn: Any, name: ActivationName) -> Any:
    mapping = {
        ActivationName.RELU: nn.ReLU,
        ActivationName.GELU: nn.GELU,
        ActivationName.TANH: nn.Tanh,
        ActivationName.SIGMOID: nn.Sigmoid,
        ActivationName.IDENTITY: nn.Identity,
    }
    return mapping[name]()


def build_mlp(spec: NeuralModelSpec) -> Any:
    """Build an ``nn.Sequential`` MLP from a declarative spec."""
    torch, nn = _require_torch()
    del torch  # used only for import side-effect / availability

    layers: list[Any] = []
    dims = [spec.input_dim, *spec.hidden_dims, spec.output_dim]
    for i in range(len(dims) - 1):
        layers.append(nn.Linear(dims[i], dims[i + 1]))
        if i < len(dims) - 2:
            layers.append(_activation(nn, spec.activation))
            if spec.dropout > 0:
                layers.append(nn.Dropout(spec.dropout))
    return nn.Sequential(*layers)
