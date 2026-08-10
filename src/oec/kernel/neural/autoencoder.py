"""Autoencoder train (N2) — merit: PyTorch."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.seeding import (
    configure_torch_seeds,
    state_dict_to_jsonable,
    torch_version,
)
from oec.neural.hashing import dataset_fingerprint, model_spec_fingerprint


def _require_torch() -> Any:
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise TorchNotAvailableError(
            "PyTorch is not installed. Install with: uv sync --extra neural"
        ) from exc
    return torch, nn


def build_autoencoder(
    input_dim: int,
    latent_dim: int,
    hidden_dims: list[int],
    *,
    activation: str = "relu",
) -> Any:
    torch, nn = _require_torch()
    act_map = {
        "relu": nn.ReLU,
        "gelu": nn.GELU,
        "tanh": nn.Tanh,
        "sigmoid": nn.Sigmoid,
    }
    act_cls = act_map.get(activation, nn.ReLU)

    enc_layers: list[Any] = []
    dims = [input_dim, *hidden_dims, latent_dim]
    for i in range(len(dims) - 1):
        enc_layers.append(nn.Linear(dims[i], dims[i + 1]))
        if i < len(dims) - 2:
            enc_layers.append(act_cls())
    encoder = nn.Sequential(*enc_layers)

    dec_layers: list[Any] = []
    rev = [latent_dim, *reversed(hidden_dims), input_dim]
    for i in range(len(rev) - 1):
        dec_layers.append(nn.Linear(rev[i], rev[i + 1]))
        if i < len(rev) - 2:
            dec_layers.append(act_cls())
    decoder = nn.Sequential(*dec_layers)

    class _AE(nn.Module):  # type: ignore[misc, name-defined]
        def __init__(self) -> None:
            super().__init__()
            self.encoder = encoder
            self.decoder = decoder

        def forward(self, x: Any) -> Any:
            z = self.encoder(x)
            return self.decoder(z)

        def encode(self, x: Any) -> Any:
            return self.encoder(x)

    return _AE()


def train_autoencoder(
    x: list[list[float]],
    *,
    latent_dim: int = 8,
    hidden_dims: list[int] | None = None,
    epochs: int = 50,
    batch_size: int = 32,
    lr: float = 1e-3,
    seed: int = 42,
    device: str = "cpu",
    noise_std: float = 0.0,
    activation: str = "relu",
) -> dict[str, Any]:
    """Train AE or denoising AE (noise_std > 0)."""
    torch, nn = _require_torch()
    hidden = hidden_dims or [32, 16]
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("x must be 2D [n, d]")
    n, d = arr.shape
    resolved, det = configure_torch_seeds(seed, device)
    model = build_autoencoder(d, latent_dim, hidden, activation=activation).to(resolved)
    optim = torch.optim.Adam(model.parameters(), lr=lr)
    crit = nn.MSELoss()
    x_t = torch.tensor(arr, dtype=torch.float32, device=resolved)
    history: list[dict[str, float]] = []
    model.train()
    for epoch in range(epochs):
        perm = torch.randperm(n, device=resolved)
        total = 0.0
        batches = 0
        for start in range(0, n, batch_size):
            idx = perm[start : start + batch_size]
            xb = x_t[idx]
            inp = xb
            if noise_std > 0:
                inp = xb + noise_std * torch.randn_like(xb)
            optim.zero_grad(set_to_none=True)
            recon = model(inp)
            loss = crit(recon, xb)
            loss.backward()
            optim.step()
            total += float(loss.item())
            batches += 1
        history.append({"epoch": float(epoch + 1), "train_mse": total / max(batches, 1)})

    model.eval()
    with torch.no_grad():
        recon = model(x_t).cpu().numpy()
        z = model.encode(x_t).cpu().numpy()
    mse = float(np.mean((recon - arr) ** 2))
    spec = {
        "architecture": "autoencoder",
        "input_dim": d,
        "latent_dim": latent_dim,
        "hidden_dims": hidden,
        "activation": activation,
        "noise_std": noise_std,
    }
    kind: Literal["basic", "denoising"] = "denoising" if noise_std > 0 else "basic"
    return {
        "task": f"autoencoder_{kind}",
        "backend": "torch",
        "backend_version": torch_version(),
        "device": resolved,
        "seed": seed,
        "deterministic_status": det,
        "epochs_ran": epochs,
        "train_metrics": {"mse": mse},
        "history": history[-5:],
        "checkpoint": {
            "architecture": "autoencoder",
            "model_spec": spec,
            "state_dict": state_dict_to_jsonable(model.state_dict()),
            "task": f"autoencoder_{kind}",
        },
        "latent_dim": latent_dim,
        "embeddings_sample": z[: min(5, n)].tolist(),
        "n_train": n,
        "dataset_fingerprint": dataset_fingerprint(x, [0.0] * n),
        "model_fingerprint": model_spec_fingerprint(spec),
        "noise_std": noise_std,
    }
