"""Torch builders for zip leftover blocks (catalog 0.2.5). Lazy torch via args."""

from __future__ import annotations

import math
from typing import Any

from oec.neural.architecture.errors import ArchitectureValidationError


def build_zip_block(torch: Any, nn: Any, block_id: str, config: dict[str, Any]) -> Any:
    if block_id == "glu":
        return _glu(nn, config)
    if block_id == "residual_conv":
        return _residual_conv(nn, config)
    if block_id == "conv3d":
        return _conv3d(nn, config)
    if block_id == "hybrid_kan":
        return _hybrid_kan(torch, nn, config)
    if block_id == "lif_spike":
        return _lif_spike(nn, config)
    if block_id == "residual_stack":
        return _residual_stack(nn, config)
    if block_id == "bottleneck":
        return _bottleneck(nn, config)
    if block_id == "inception":
        return _inception(nn, config)
    if block_id == "dense_block":
        return _dense_block(nn, config)
    if block_id == "fusion":
        return _fusion(nn, config)
    if block_id == "message_passing_stack":
        return _message_passing_stack(torch, nn, config)
    if block_id == "encoder_decoder":
        return _encoder_decoder(nn, config)
    if block_id == "vae":
        return _vae(nn, config)
    if block_id == "gan_generator":
        return _gan_generator(nn, config)
    if block_id == "gan_discriminator":
        return _gan_discriminator(nn, config)
    if block_id == "moe":
        return _moe(nn, config)
    if block_id == "siamese":
        return _siamese(nn, config)
    if block_id == "diffusion_denoiser":
        return _diffusion_denoiser(nn, config)
    if block_id == "global_avg_pool_3d":
        return _gap3d(nn)
    raise ArchitectureValidationError(f"no torch builder for block {block_id!r}")


def _glu(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 16))

    class GLU(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.proj = nn.Linear(in_f, 2 * hidden)
            self.out = nn.Linear(hidden, in_f)

        def forward(self, x: Any) -> Any:
            a, b = self.proj(x).chunk(2, dim=-1)
            return self.out(a * b.sigmoid())

    return GLU()


def _residual_conv(nn: Any, config: dict[str, Any]) -> Any:
    in_ch = int(config["in_channels"])
    out_ch = int(config["out_channels"])
    kernel = int(config.get("kernel_size", 3))
    pad = kernel // 2

    class ResidualConv(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.conv = nn.Sequential(
                nn.Conv2d(in_ch, out_ch, kernel_size=kernel, padding=pad),
                nn.ReLU(),
                nn.Conv2d(out_ch, out_ch, kernel_size=kernel, padding=pad),
            )
            self.skip = (
                nn.Identity() if in_ch == out_ch else nn.Conv2d(in_ch, out_ch, kernel_size=1)
            )
            self.act = nn.ReLU()

        def forward(self, x: Any) -> Any:
            return self.act(self.conv(x) + self.skip(x))

    return ResidualConv()


def _conv3d(nn: Any, config: dict[str, Any]) -> Any:
    return nn.Conv3d(
        int(config["in_channels"]),
        int(config["out_channels"]),
        kernel_size=int(config["kernel_size"]),
        padding=1,
    )


def _hybrid_kan(torch: Any, nn: Any, config: dict[str, Any]) -> Any:
    from oec.kernel.neural.architecture_build import _kan_module

    kan = _kan_module(torch, nn, config)
    in_f = int(config["in_features"])
    out_f = int(config["out_features"])
    hidden = int(config.get("hidden_dim", 16))

    class HybridKAN(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.kan = kan
            self.mlp = nn.Sequential(nn.Linear(in_f, hidden), nn.GELU(), nn.Linear(hidden, out_f))

        def forward(self, x: Any) -> Any:
            return self.kan(x) + self.mlp(x)

    return HybridKAN()


def _lif_spike(nn: Any, config: dict[str, Any]) -> Any:
    threshold = float(config.get("threshold", 1.0))
    decay = float(config.get("decay", 0.9))

    class LIFSpike(nn.Module):  # type: ignore[misc]
        def forward(self, x: Any) -> Any:
            torch = __import__("torch")
            if x.dim() == 2:
                x = x.unsqueeze(1)
            if x.dim() != 3:
                raise ArchitectureValidationError(
                    f"lif_spike expects rank 2 or 3; got rank {x.dim()}"
                )
            batch, steps, feat = x.shape
            voltage = x.new_zeros(batch, feat)
            spikes = []
            for t in range(steps):
                voltage = decay * voltage + x[:, t]
                spike = (voltage > threshold).to(dtype=x.dtype)
                voltage = voltage * (1.0 - spike)
                spikes.append(spike)
            return torch.stack(spikes, dim=1)

    return LIFSpike()


def _residual_stack(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 16))
    n_layers = int(config.get("n_layers", 2))

    class ResidualStack(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.layers = nn.ModuleList(
                [
                    nn.Sequential(nn.Linear(in_f, hidden), nn.GELU(), nn.Linear(hidden, in_f))
                    for _ in range(n_layers)
                ]
            )

        def forward(self, x: Any) -> Any:
            hidden_state = x
            for layer in self.layers:
                hidden_state = hidden_state + layer(hidden_state)
            return hidden_state

    return ResidualStack()


def _bottleneck(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 4))
    return nn.Sequential(nn.Linear(in_f, hidden), nn.GELU(), nn.Linear(hidden, in_f))


def _inception(nn: Any, config: dict[str, Any]) -> Any:
    in_ch = int(config["in_channels"])
    out_ch = int(config["out_channels"])
    branch = max(out_ch // 3, 1)

    class Inception(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.b1 = nn.Conv2d(in_ch, branch, kernel_size=1)
            self.b3 = nn.Conv2d(in_ch, branch, kernel_size=3, padding=1)
            self.b5 = nn.Conv2d(in_ch, branch, kernel_size=5, padding=2)
            self.proj = nn.Conv2d(3 * branch, out_ch, kernel_size=1)
            self.act = nn.ReLU()

        def forward(self, x: Any) -> Any:
            torch = __import__("torch")
            cat = torch.cat([self.b1(x), self.b3(x), self.b5(x)], dim=1)
            return self.act(self.proj(cat))

    return Inception()


def _dense_block(nn: Any, config: dict[str, Any]) -> Any:
    in_ch = int(config["in_channels"])
    growth = int(config.get("growth_rate", 4))
    n_layers = int(config.get("n_layers", 2))
    out_ch = int(config["out_channels"])

    class DenseBlock(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.layers = nn.ModuleList()
            channels = in_ch
            for _ in range(n_layers):
                self.layers.append(nn.Conv2d(channels, growth, kernel_size=3, padding=1))
                channels += growth
            self.proj = nn.Conv2d(channels, out_ch, kernel_size=1)
            self.act = nn.ReLU()

        def forward(self, x: Any) -> Any:
            torch = __import__("torch")
            features = x
            for layer in self.layers:
                grown = self.act(layer(features))
                features = torch.cat([features, grown], dim=1)
            return self.proj(features)

    return DenseBlock()


def _fusion(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    out_f = int(config.get("out_features", 8))

    class Fusion(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.proj = nn.Linear(2 * in_f, out_f)

        def forward(self, a: Any, b: Any) -> Any:
            torch = __import__("torch")
            return self.proj(torch.cat([a, b], dim=-1))

    return Fusion()


def _message_passing_stack(torch: Any, nn: Any, config: dict[str, Any]) -> Any:
    from oec.kernel.neural.architecture_build import _gnn_block

    inner = _gnn_block(torch, nn, "gcn", config)

    class MessagePassingStack(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.inner = inner

        def forward(self, x: Any, edge_index: Any) -> Any:
            out = self.inner(x, edge_index)
            if out.shape[-1] == x.shape[-1]:
                return x + out
            return out

    return MessagePassingStack()


def _encoder_decoder(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    latent = int(config["latent_dim"])
    out_f = int(config["out_features"])
    return nn.Sequential(
        nn.Linear(in_f, latent),
        nn.GELU(),
        nn.Linear(latent, out_f),
    )


def _vae(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    latent = int(config["latent_dim"])
    out_f = int(config["out_features"])

    class VAE(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.encoder = nn.Linear(in_f, 2 * latent)
            self.decoder = nn.Sequential(nn.Linear(latent, out_f))
            self.kl = None

        def forward(self, x: Any) -> Any:
            torch = __import__("torch")
            stats = self.encoder(x)
            mu, logvar = stats.chunk(2, dim=-1)
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            z = mu + eps * std
            self.kl = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
            return self.decoder(z)

    return VAE()


def _gan_generator(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    hidden = int(config.get("hidden_dim", 16))
    out_f = int(config["out_features"])
    return nn.Sequential(nn.Linear(in_f, hidden), nn.ReLU(), nn.Linear(hidden, out_f), nn.Tanh())


def _gan_discriminator(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    hidden = int(config.get("hidden_dim", 16))
    out_f = int(config.get("out_features", 1))
    return nn.Sequential(nn.Linear(in_f, hidden), nn.LeakyReLU(0.2), nn.Linear(hidden, out_f))


def _moe(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    hidden = int(config.get("hidden_dim", 16))
    out_f = int(config["out_features"])
    n_experts = int(config.get("n_experts", 4))

    class MoE(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.gate = nn.Linear(in_f, n_experts)
            self.experts = nn.ModuleList(
                [
                    nn.Sequential(nn.Linear(in_f, hidden), nn.GELU(), nn.Linear(hidden, out_f))
                    for _ in range(n_experts)
                ]
            )

        def forward(self, x: Any) -> Any:
            torch = __import__("torch")
            weights = torch.softmax(self.gate(x), dim=-1)
            stacked = torch.stack([expert(x) for expert in self.experts], dim=1)
            return (stacked * weights.unsqueeze(-1)).sum(dim=1)

    return MoE()


def _siamese(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    hidden = int(config.get("hidden_dim", 16))
    out_f = int(config.get("out_features", 1))

    class Siamese(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.encoder = nn.Sequential(nn.Linear(in_f, hidden), nn.ReLU())
            self.head = nn.Linear(hidden, out_f)

        def forward(self, left: Any, right: Any) -> Any:
            return self.head((self.encoder(left) - self.encoder(right)).abs())

    return Siamese()


def _diffusion_denoiser(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    hidden = int(config.get("hidden_dim", 16))
    time_dim = int(config.get("time_dim", 4))

    class DiffusionDenoiser(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.time_embed = nn.Linear(time_dim, in_f)
            self.net = nn.Sequential(nn.Linear(in_f, hidden), nn.SiLU(), nn.Linear(hidden, in_f))

        def forward(self, x: Any) -> Any:
            torch = __import__("torch")
            batch = x.shape[0]
            half = max(time_dim // 2, 1)
            freqs = torch.exp(
                torch.linspace(0, -math.log(10000.0), half, device=x.device, dtype=x.dtype)
            )
            t = torch.zeros(batch, 1, device=x.device, dtype=x.dtype)
            args = t * freqs.unsqueeze(0)
            emb = torch.cat([torch.sin(args), torch.cos(args)], dim=-1)
            if emb.shape[-1] < time_dim:
                emb = torch.nn.functional.pad(emb, (0, time_dim - emb.shape[-1]))
            else:
                emb = emb[:, :time_dim]
            return x + self.net(x) + self.time_embed(emb)

    return DiffusionDenoiser()


def _gap3d(nn: Any) -> Any:
    class Pool(nn.Module):  # type: ignore[misc]
        def forward(self, x: Any) -> Any:
            return x.mean(dim=(-3, -2, -1))

    return Pool()
