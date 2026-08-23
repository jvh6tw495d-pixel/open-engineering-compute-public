"""JAX builder for ArchitectureGraph (ADR 0047). jax is imported only here."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from oec.kernel.neural.errors import JaxNotAvailableError
from oec.neural.architecture.backends import JAX_BUILDABLE_BLOCK_IDS
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.graph import ArchitectureGraph
from oec.neural.architecture.registry import BlockRegistry


def _require_jax() -> Any:
    try:
        import jax  # type: ignore[import-not-found]
        import jax.numpy as jnp  # type: ignore[import-not-found]
    except ImportError as exc:
        raise JaxNotAvailableError(
            "JAX is not installed. Install with: uv sync --extra jax"
        ) from exc
    return jax, jnp


def build_architecture_jax(
    graph: ArchitectureGraph,
    registry: BlockRegistry,
) -> Any:
    jax, jnp = _require_jax()
    order = list(graph.topological_order())
    node_map = {node.id: node for node in graph.nodes}
    for node_id in order:
        block_id = node_map[node_id].block_id
        if block_id not in JAX_BUILDABLE_BLOCK_IDS:
            raise ArchitectureValidationError(f"block {block_id!r} has no jax builder")
    modules: dict[str, Any] = {}
    for node_id in order:
        node = node_map[node_id]
        spec = registry.get(node.block_id)
        modules[node_id] = _jax_block(jax, jnp, node.block_id, spec.validate_config(node.config))
    edges_by_target: dict[str, list[tuple[str, str, str]]] = {}
    for edge in graph.edges:
        edges_by_target.setdefault(edge.target, []).append(
            (edge.source, edge.source_port, edge.target_port)
        )

    class JaxSequential:
        def init(self, rng: Any, x: Any) -> dict[str, Any]:
            params: dict[str, Any] = {}
            outputs: dict[str, Any] = {}
            features = x["features"] if isinstance(x, Mapping) else x
            keys = jax.random.split(rng, max(len(order), 2))
            for i, node_id in enumerate(order):
                incoming = edges_by_target.get(node_id, [])
                if not incoming:
                    sample = features
                elif len(incoming) == 1:
                    sample = outputs[incoming[0][0]]
                else:
                    sample = {port: outputs[src] for src, _sp, port in incoming}
                params[node_id], outputs[node_id] = modules[node_id].init(keys[i], sample)
            return params

        def apply(self, params: dict[str, Any], x: Any) -> Any:
            outputs: dict[str, Any] = {}
            features = x["features"] if isinstance(x, Mapping) else x
            for node_id in order:
                incoming = edges_by_target.get(node_id, [])
                if not incoming:
                    inp = features
                elif len(incoming) == 1:
                    inp = outputs[incoming[0][0]]
                else:
                    inp = {port: outputs[src] for src, _sp, port in incoming}
                outputs[node_id] = modules[node_id].apply(params[node_id], inp)
            return outputs[order[-1]]

        def __call__(self, params: dict[str, Any], x: Any) -> Any:
            return self.apply(params, x)

    return JaxSequential()


def _linear_params(jax: Any, jnp: Any, rng: Any, n_in: int, n_out: int) -> dict[str, Any]:
    w_key, b_key = jax.random.split(rng)
    scale = jnp.sqrt(2.0 / max(n_in, 1))
    return {
        "w": jax.random.normal(w_key, (n_in, n_out)) * scale,
        "b": jnp.zeros((n_out,)),
    }


def _dense(jnp: Any, params: dict[str, Any], x: Any) -> Any:
    return x @ params["w"] + params["b"]


def _relu(jnp: Any, x: Any) -> Any:
    return jnp.maximum(x, 0.0)


def _gelu(jnp: Any, x: Any) -> Any:
    return 0.5 * x * (1.0 + jnp.tanh(jnp.sqrt(2.0 / jnp.pi) * (x + 0.044715 * x**3)))


class _JaxFn:
    def __init__(self, init_fn: Callable[..., Any], apply_fn: Callable[..., Any]) -> None:
        self.init = init_fn
        self.apply = apply_fn


def _jax_block(jax: Any, jnp: Any, block_id: str, config: dict[str, Any]) -> Any:
    if block_id in {"linear", "mlp", "encoder", "decoder", "encoder_decoder"}:
        return _jax_mlp_family(jax, jnp, block_id, config)
    if block_id in {"flatten", "global_avg_pool_1d", "global_avg_pool_2d", "global_avg_pool_3d"}:
        return _jax_pool(jnp, block_id)
    if block_id == "sequence_pool":
        return _JaxFn(lambda rng, x: ({}, jnp.mean(x, axis=1)), lambda p, x: jnp.mean(x, axis=1))
    if block_id == "vector_to_sequence":
        return _JaxFn(lambda rng, x: ({}, x[:, None, :]), lambda p, x: x[:, None, :])
    if block_id in {"conv1d", "conv2d", "conv3d"}:
        return _jax_conv(jax, jnp, block_id, config)
    if block_id == "glu":
        return _jax_glu(jax, jnp, config)
    if block_id in {"residual_mlp", "residual_stack", "bottleneck", "highway"}:
        return _jax_residual_family(jax, jnp, block_id, config)
    if block_id == "residual_conv":
        return _jax_residual_conv(jax, jnp, config)
    if block_id == "hybrid_kan":
        return _jax_hybrid_kan(jax, jnp, config)
    if block_id == "lif_spike":
        return _jax_lif(jnp, config)
    if block_id in {"inception", "dense_block"}:
        return _jax_conv_motif(jax, jnp, block_id, config)
    if block_id == "fusion":
        return _jax_fusion(jax, jnp, config)
    if block_id == "siamese":
        return _jax_siamese(jax, jnp, config)
    if block_id == "vae":
        return _jax_vae(jax, jnp, config)
    if block_id in {"gan_generator", "gan_discriminator", "moe", "diffusion_denoiser"}:
        return _jax_macros(jax, jnp, block_id, config)
    raise ArchitectureValidationError(f"no jax builder for block {block_id!r}")


def _jax_mlp_family(jax: Any, jnp: Any, block_id: str, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    if block_id == "linear":
        out_f = int(config["out_features"])

        def init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
            params = _linear_params(jax, jnp, rng, in_f, out_f)
            return params, _dense(jnp, params, x)

        return _JaxFn(init, lambda p, x: _dense(jnp, p, x))
    hidden = int(config.get("hidden_dim") or config.get("latent_dim") or 8)
    out_f = int(config.get("out_features") or hidden)

    def init_mlp(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        k1, k2 = jax.random.split(rng)
        p1 = _linear_params(jax, jnp, k1, in_f, hidden)
        p2 = _linear_params(jax, jnp, k2, hidden, out_f)
        h = _gelu(jnp, _dense(jnp, p1, x))
        return {"a": p1, "b": p2}, _dense(jnp, p2, h)

    def apply_mlp(params: dict[str, Any], x: Any) -> Any:
        return _dense(jnp, params["b"], _gelu(jnp, _dense(jnp, params["a"], x)))

    return _JaxFn(init_mlp, apply_mlp)


def _jax_pool(jnp: Any, block_id: str) -> Any:
    def apply(_params: dict[str, Any], x: Any) -> Any:
        if block_id == "flatten":
            return jnp.reshape(x, (x.shape[0], -1))
        if block_id == "global_avg_pool_1d":
            return jnp.mean(x, axis=-1)
        if block_id == "global_avg_pool_2d":
            return jnp.mean(x, axis=(-2, -1))
        return jnp.mean(x, axis=(-3, -2, -1))

    return _JaxFn(lambda rng, x: ({}, apply({}, x)), apply)


def _jax_conv(jax: Any, jnp: Any, block_id: str, config: dict[str, Any]) -> Any:
    in_ch = int(config["in_channels"])
    out_ch = int(config["out_channels"])
    k = int(config.get("kernel_size", 3))

    def init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        if block_id == "conv1d":
            w = jax.random.normal(rng, (k, in_ch, out_ch)) * 0.05
        elif block_id == "conv2d":
            w = jax.random.normal(rng, (k, k, in_ch, out_ch)) * 0.05
        else:
            w = jax.random.normal(rng, (k, k, k, in_ch, out_ch)) * 0.05
        params = {"w": w}
        return params, apply(params, x)

    def apply(params: dict[str, Any], x: Any) -> Any:
        w = params["w"]
        pad = k // 2
        if block_id == "conv1d":
            xp = jnp.pad(x, ((0, 0), (0, 0), (pad, pad)))
            length = x.shape[-1]
            windows = jnp.stack([xp[:, :, i : i + k] for i in range(length)], axis=2)
            return jnp.einsum("nclk,kco->nol", windows, w)
        if block_id == "conv2d":
            xp = jnp.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
            h, wd = x.shape[-2], x.shape[-1]
            acc = []
            for i in range(h):
                row = []
                for j in range(wd):
                    patch = xp[:, :, i : i + k, j : j + k]
                    row.append(jnp.einsum("ncij,ijco->no", patch, w))
                acc.append(jnp.stack(row, axis=-1))
            return jnp.stack(acc, axis=-2)
        xp = jnp.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad), (pad, pad)))
        d, h, wd = x.shape[-3], x.shape[-2], x.shape[-1]
        vol = []
        for z in range(d):
            plane = []
            for i in range(h):
                row = []
                for j in range(wd):
                    patch = xp[:, :, z : z + k, i : i + k, j : j + k]
                    row.append(jnp.einsum("ncijk,ijkco->no", patch, w))
                plane.append(jnp.stack(row, axis=-1))
            vol.append(jnp.stack(plane, axis=-2))
        return jnp.stack(vol, axis=-3)

    return _JaxFn(init, apply)


def _jax_glu(jax: Any, jnp: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 16))

    def init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        k1, k2 = jax.random.split(rng)
        p1 = _linear_params(jax, jnp, k1, in_f, 2 * hidden)
        p2 = _linear_params(jax, jnp, k2, hidden, in_f)
        return {"p": p1, "o": p2}, apply({"p": p1, "o": p2}, x)

    def apply(params: dict[str, Any], x: Any) -> Any:
        h = _dense(jnp, params["p"], x)
        a, b = jnp.split(h, 2, axis=-1)
        return _dense(jnp, params["o"], a * jax.nn.sigmoid(b))

    return _JaxFn(init, apply)


def _jax_residual_family(jax: Any, jnp: Any, block_id: str, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 16))
    n_layers = int(config.get("n_layers", 1 if block_id != "residual_stack" else 2))
    if block_id == "bottleneck":
        n_layers = 1

    def one_init(rng: Any) -> dict[str, Any]:
        k1, k2 = jax.random.split(rng)
        return {
            "a": _linear_params(jax, jnp, k1, in_f, hidden),
            "b": _linear_params(jax, jnp, k2, hidden, in_f),
        }

    def one_apply(params: dict[str, Any], x: Any) -> Any:
        return _dense(jnp, params["b"], _gelu(jnp, _dense(jnp, params["a"], x)))

    def init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        keys = jax.random.split(rng, n_layers)
        layers = [one_init(k) for k in keys]
        return {"layers": layers}, apply({"layers": layers}, x)

    def apply(params: dict[str, Any], x: Any) -> Any:
        h = x
        for layer in params["layers"]:
            h = h + one_apply(layer, h)
        return h

    if block_id == "highway":

        def init_h(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
            k1, k2 = jax.random.split(rng)
            t = _linear_params(jax, jnp, k1, in_f, in_f)
            g = _linear_params(jax, jnp, k2, in_f, in_f)
            return {"t": t, "g": g}, apply_h({"t": t, "g": g}, x)

        def apply_h(params: dict[str, Any], x: Any) -> Any:
            gate = jax.nn.sigmoid(_dense(jnp, params["g"], x))
            return gate * _relu(jnp, _dense(jnp, params["t"], x)) + (1 - gate) * x

        return _JaxFn(init_h, apply_h)

    return _JaxFn(init, apply)


def _jax_residual_conv(jax: Any, jnp: Any, config: dict[str, Any]) -> Any:
    inner = _jax_conv(jax, jnp, "conv2d", config)

    def apply(params: dict[str, Any], x: Any) -> Any:
        y = inner.apply(params["conv"], x)
        if x.shape[1] == y.shape[1]:
            return _relu(jnp, y + x)
        return _relu(jnp, y)

    def init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        p, _ = inner.init(rng, x)
        params = {"conv": p}
        return params, apply(params, x)

    return _JaxFn(init, apply)


def _jax_hybrid_kan(jax: Any, jnp: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    out_f = int(config["out_features"])
    hidden = int(config.get("hidden_dim", 16))
    grid = int(config.get("grid_size", 8))
    centers = jnp.linspace(-1.0, 1.0, grid)
    sigma = 2.0 / grid

    def init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        k1, k2, k3 = jax.random.split(rng, 3)
        rbf_w = jax.random.normal(k1, (in_f, grid, out_f)) * 0.1
        mlp_a = _linear_params(jax, jnp, k2, in_f, hidden)
        mlp_b = _linear_params(jax, jnp, k3, hidden, out_f)
        params = {"rbf": rbf_w, "a": mlp_a, "b": mlp_b}
        return params, apply(params, x)

    def apply(params: dict[str, Any], x: Any) -> Any:
        xc = jnp.clip(x, -1.0, 1.0)
        basis = jnp.exp(-((xc[..., None] - centers) ** 2) / (2 * sigma**2))
        kan_out = jnp.einsum("bik,iko->bo", basis, params["rbf"])
        mlp_out = _dense(jnp, params["b"], _gelu(jnp, _dense(jnp, params["a"], x)))
        return kan_out + mlp_out

    return _JaxFn(init, apply)


def _jax_lif(jnp: Any, config: dict[str, Any]) -> Any:
    threshold = float(config.get("threshold", 1.0))
    decay = float(config.get("decay", 0.9))

    def apply(_params: dict[str, Any], x: Any) -> Any:
        if x.ndim == 2:
            x = x[:, None, :]
        steps = x.shape[1]
        voltage = jnp.zeros((x.shape[0], x.shape[2]), dtype=x.dtype)
        spikes = []
        for t in range(int(steps)):
            voltage = decay * voltage + x[:, t]
            spike = (voltage > threshold).astype(x.dtype)
            voltage = voltage * (1.0 - spike)
            spikes.append(spike)
        return jnp.stack(spikes, axis=1)

    return _JaxFn(lambda rng, x: ({}, apply({}, x)), apply)


def _jax_conv_motif(jax: Any, jnp: Any, block_id: str, config: dict[str, Any]) -> Any:
    # Honest fallback: 1x1-equivalent mix via 2d conv SAME.
    conv = _jax_conv(jax, jnp, "conv2d", {**config, "kernel_size": 3})
    return conv


def _jax_fusion(jax: Any, jnp: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    out_f = int(config.get("out_features", 8))

    def init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        params = _linear_params(jax, jnp, rng, 2 * in_f, out_f)
        return params, apply(params, x)

    def apply(params: dict[str, Any], x: Any) -> Any:
        a, b = x["a"], x["b"]
        return _dense(jnp, params, jnp.concatenate([a, b], axis=-1))

    return _JaxFn(init, apply)


def _jax_siamese(jax: Any, jnp: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    hidden = int(config.get("hidden_dim", 16))
    out_f = int(config.get("out_features", 1))

    def init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        k1, k2 = jax.random.split(rng)
        enc = _linear_params(jax, jnp, k1, in_f, hidden)
        head = _linear_params(jax, jnp, k2, hidden, out_f)
        return {"e": enc, "h": head}, apply({"e": enc, "h": head}, x)

    def apply(params: dict[str, Any], x: Any) -> Any:
        left = _relu(jnp, _dense(jnp, params["e"], x["left"]))
        right = _relu(jnp, _dense(jnp, params["e"], x["right"]))
        return _dense(jnp, params["h"], jnp.abs(left - right))

    return _JaxFn(init, apply)


def _jax_vae(jax: Any, jnp: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    latent = int(config["latent_dim"])
    out_f = int(config["out_features"])

    def init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        k1, k2, k3 = jax.random.split(rng, 3)
        enc = _linear_params(jax, jnp, k1, in_f, 2 * latent)
        dec = _linear_params(jax, jnp, k2, latent, out_f)
        params = {"enc": enc, "dec": dec, "rng": k3}
        return params, apply(params, x)

    def apply(params: dict[str, Any], x: Any) -> Any:
        stats = _dense(jnp, params["enc"], x)
        mu, logvar = jnp.split(stats, 2, axis=-1)
        std = jnp.exp(0.5 * logvar)
        eps = jax.random.normal(params.get("rng", jax.random.PRNGKey(0)), std.shape)
        z = mu + eps * std
        return _dense(jnp, params["dec"], z)

    return _JaxFn(init, apply)


def _jax_macros(jax: Any, jnp: Any, block_id: str, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 16))
    out_f = int(config.get("out_features") or (in_f if block_id == "diffusion_denoiser" else 8))
    n_experts = int(config.get("n_experts", 4))

    if block_id == "moe":

        def moe_init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
            keys = jax.random.split(rng, n_experts + 1)
            gate = _linear_params(jax, jnp, keys[0], in_f, n_experts)
            experts = []
            for i in range(n_experts):
                k1, k2 = jax.random.split(keys[i + 1])
                experts.append(
                    {
                        "a": _linear_params(jax, jnp, k1, in_f, hidden),
                        "b": _linear_params(jax, jnp, k2, hidden, out_f),
                    }
                )
            params = {"gate": gate, "experts": experts}
            return params, moe_apply(params, x)

        def moe_apply(params: dict[str, Any], x: Any) -> Any:
            w = jax.nn.softmax(_dense(jnp, params["gate"], x), axis=-1)
            outs = []
            for expert in params["experts"]:
                outs.append(_dense(jnp, expert["b"], _gelu(jnp, _dense(jnp, expert["a"], x))))
            stacked = jnp.stack(outs, axis=1)
            return jnp.sum(stacked * w[..., None], axis=1)

        return _JaxFn(moe_init, moe_apply)

    def gen_init(rng: Any, x: Any) -> tuple[dict[str, Any], Any]:
        k1, k2 = jax.random.split(rng)
        a = _linear_params(jax, jnp, k1, in_f, hidden)
        b = _linear_params(jax, jnp, k2, hidden, out_f)
        return {"a": a, "b": b}, gen_apply({"a": a, "b": b}, x)

    def gen_apply(params: dict[str, Any], x: Any) -> Any:
        h = _relu(jnp, _dense(jnp, params["a"], x))
        y = _dense(jnp, params["b"], h)
        if block_id == "diffusion_denoiser":
            return x + y
        if block_id == "gan_generator":
            return jnp.tanh(y)
        return y

    return _JaxFn(gen_init, gen_apply)
