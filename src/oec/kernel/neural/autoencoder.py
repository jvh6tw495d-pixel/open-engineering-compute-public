"""Autoencoder train (N2) — merit: PyTorch."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.runtime import (
    count_parameters,
    enforce_max_params,
    fit_minibatches,
    prepare_device_and_seeds,
    save_checkpoint,
)
from oec.kernel.neural.seeding import torch_version
from oec.neural.contracts import DeviceSpec, OptimizerName, OptimizerSpec
from oec.neural.hashing import dataset_fingerprint, model_spec_fingerprint
from oec.neural.runtime import CapacityName, TrainingRuntimeSpec


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
    x: Any,
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
    runtime: TrainingRuntimeSpec | None = None,
    capacity: CapacityName | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Train AE or denoising AE (noise_std > 0)."""
    torch, nn = _require_torch()
    hidden = hidden_dims or [32, 16]
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("x must be 2D [n, d]")
    n, d = arr.shape
    rt = runtime or TrainingRuntimeSpec(
        seed=seed,
        device=DeviceSpec(device=device),
        epochs=epochs,
        batch_size=batch_size,
        optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=lr),
        early_stopping_patience=None,
    )
    resolved, det = prepare_device_and_seeds(rt)
    model = build_autoencoder(d, latent_dim, hidden, activation=activation).to(resolved)
    n_params = count_parameters(model)
    enforce_max_params(n_params, rt.max_params)
    crit = nn.MSELoss()
    x_t = torch.tensor(arr, dtype=torch.float32, device=resolved)

    noise = float(noise_std)

    def _noise_transform(xb: Any, yb: Any) -> tuple[Any, Any]:
        # yb ignored; reconstruct clean xb from possibly noisy inp
        if noise > 0:
            return xb + noise * torch.randn_like(xb), xb
        return xb, xb

    history, epochs_ran = fit_minibatches(
        model,
        x_t,
        x_t,  # target placeholder; transform replaces
        crit,
        rt,
        device=resolved,
        multiclass=False,
        input_transform=_noise_transform if noise > 0 else (lambda xb, yb: (xb, xb)),
    )

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
    meta = {
        "architecture": "autoencoder",
        "model_spec": spec,
        "task": f"autoencoder_{kind}",
        "n_params": n_params,
        "capacity": capacity,
    }
    ckpt, cref = save_checkpoint(
        storage=rt.checkpoint_storage,
        state_dict=model.state_dict(),
        meta=meta,
        run_id=run_id,
    )
    return {
        "task": f"autoencoder_{kind}",
        "backend": "torch",
        "backend_version": torch_version(),
        "device": resolved,
        "seed": rt.seed,
        "deterministic_status": det,
        "epochs_ran": epochs_ran,
        "train_metrics": {"mse": mse},
        "history": history[-5:],
        "checkpoint": ckpt,
        "checkpoint_ref": cref.model_dump(mode="json"),
        "latent_dim": latent_dim,
        "embeddings_sample": z[: min(5, n)].tolist(),
        "n_train": n,
        "n_params": n_params,
        "capacity": capacity,
        "runtime": {
            "lr_scheduler": rt.lr_scheduler,
            "grad_clip": rt.grad_clip,
            "amp": rt.amp,
            "max_params": rt.max_params,
            "checkpoint_storage": rt.checkpoint_storage,
        },
        "dataset_fingerprint": dataset_fingerprint(arr.tolist(), [0.0] * n),
        "model_fingerprint": model_spec_fingerprint(spec),
        "noise_std": noise_std,
    }
