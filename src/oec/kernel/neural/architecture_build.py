"""Build a torch.nn.Module from ArchitectureGraph (ADR 0047 waves A7/A8/A-ports).

Torch is imported only inside ``build_architecture``. The architecture IR
package stays core-safe. A7 materializes a strict linear chain, with one
named-port exception: a node whose block declares arity > 1 input ports
(e.g. ``cross_attention``) may have indegree == arity ("named joins").
Forks, extra skips, disconnected components, and empty graphs still fail
closed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.neural.architecture import default_registry
from oec.neural.architecture.backends import TORCH_BUILDABLE_BLOCK_IDS
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.graph import ArchitectureGraph
from oec.neural.architecture.registry import BlockRegistry
from oec.neural.architecture.types import NeuralFamily

_TORCH_BUILDERS = TORCH_BUILDABLE_BLOCK_IDS


def _require_torch() -> Any:
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise TorchNotAvailableError(
            "PyTorch is not installed. Install with: uv sync --extra neural"
        ) from exc
    return torch, nn


def build_architecture(
    graph: ArchitectureGraph,
    registry: BlockRegistry | None = None,
    *,
    backend: str = "torch",
) -> Any:
    """Materialize a strict linear chain (with named-port joins). Forks,
    disconnected components, and blocks without a torch builder fail closed.
    """
    if backend != "torch":
        raise ValueError(f"unsupported architecture backend {backend!r}")
    registry = registry or default_registry
    report = graph.validate_graph(registry)
    if not report.valid:
        raise ArchitectureValidationError("; ".join(report.errors))
    order = _require_linear_chain(graph, registry)
    node_map = {node.id: node for node in graph.nodes}
    for node_id in order:
        block_id = node_map[node_id].block_id
        if block_id not in _TORCH_BUILDERS:
            raise ArchitectureValidationError(
                f"block {block_id!r} has no torch builder in A7 "
                f"(missing backend or not in this wave)"
            )
    torch, nn = _require_torch()
    modules: dict[str, Any] = {}
    graph_node_ids: set[str] = set()
    for node_id in order:
        node = node_map[node_id]
        spec = registry.get(node.block_id)
        modules[node_id] = _build_block(torch, nn, node.block_id, spec.validate_config(node.config))
        if spec.family == NeuralFamily.GRAPH:
            graph_node_ids.add(node_id)
    edges_by_target: dict[str, list[tuple[str, str, str]]] = {}
    for edge in graph.edges:
        edges_by_target.setdefault(edge.target, []).append(
            (edge.source, edge.source_port, edge.target_port)
        )
    return _graph_sequential(nn, order, modules, edges_by_target, graph_node_ids)


def _require_linear_chain(graph: ArchitectureGraph, registry: BlockRegistry) -> list[str]:
    errors = graph.a7_chain_errors(registry)
    if errors:
        raise ArchitectureValidationError("; ".join(errors))
    return graph.topological_order()


def _build_block(torch: Any, nn: Any, block_id: str, config: dict[str, Any]) -> Any:
    if block_id in {"linear", "mlp"}:
        return _linear_or_mlp(nn, block_id, config)
    if block_id in {"encoder", "decoder"}:
        return nn.Sequential(
            nn.Linear(int(config["in_features"]), int(config["out_features"])),
            nn.GELU(),
        )
    if block_id == "flatten":
        return nn.Flatten()
    if block_id == "global_avg_pool_1d":
        return _gap1d(nn)
    if block_id == "global_avg_pool_2d":
        return _gap2d(nn)
    if block_id == "sequence_pool":
        return _sequence_pool(nn)
    if block_id == "vector_to_sequence":
        return _vector_to_sequence(nn)
    if block_id == "conv1d":
        return nn.Conv1d(
            int(config["in_channels"]),
            int(config["out_channels"]),
            kernel_size=int(config["kernel_size"]),
            padding=1,
        )
    if block_id == "conv2d":
        return nn.Conv2d(
            int(config["in_channels"]),
            int(config["out_channels"]),
            kernel_size=int(config["kernel_size"]),
            padding=1,
        )
    if block_id == "depthwise_conv2d":
        return _depthwise_conv2d(nn, config)
    if block_id == "separable_conv2d":
        return _separable_conv2d(nn, config)
    if block_id == "dilated_conv1d":
        return _dilated_conv1d(nn, config)
    if block_id == "grouped_conv2d":
        return _grouped_conv2d(nn, config)
    if block_id == "squeeze_excitation":
        return _squeeze_excitation(nn, config)
    if block_id in {"lstm", "gru"}:
        hidden = int(config["hidden_dim"])
        cls = nn.LSTM if block_id == "lstm" else nn.GRU
        return cls(
            int(config["input_size"]),
            hidden,
            num_layers=int(config["n_layers"]),
            batch_first=True,
        )
    if block_id == "tcn":
        return _tcn(nn, config)
    if block_id == "transformer_encoder":
        layer = nn.TransformerEncoderLayer(
            d_model=int(config["d_model"]),
            nhead=int(config["nhead"]),
            dim_feedforward=int(config["dim_feedforward"]),
            batch_first=True,
        )
        return nn.TransformerEncoder(layer, num_layers=int(config["num_layers"]))
    if block_id == "self_attention":
        return _self_attention(nn, config)
    if block_id == "cross_attention":
        return _cross_attention(nn, config)
    if block_id == "swiglu":
        return _swiglu(nn, config)
    if block_id == "residual_mlp":
        return _residual_mlp(nn, config)
    if block_id == "residual_gated":
        return _residual_gated(nn, config)
    if block_id == "highway":
        return _highway(nn, config)
    if block_id == "geglu":
        return _geglu(nn, config)
    if block_id == "kan":
        return _kan_module(torch, nn, config)
    if block_id == "fno":
        return _fno_1d(torch, nn, config)
    if block_id == "fno_2d":
        return _fno_2d(torch, nn, config)
    if block_id == "local_attention":
        return _local_attention(nn, config)
    if block_id == "linear_attention":
        return _linear_attention(nn, config)
    if block_id == "neural_ode":
        return _neural_ode(nn, config)
    if block_id == "deeponet":
        return _deeponet(nn, config)
    if block_id == "pinn_motif":
        return _pinn_motif(nn, config)
    if block_id in {"gcn", "graphsage", "gat"}:
        return _gnn_block(torch, nn, block_id, config)
    if block_id in {"graph_global_pool", "graph_embedding_to_vector"}:
        return _graph_pool(nn, block_id)
    raise ArchitectureValidationError(f"no torch builder for block {block_id!r}")


def _linear_or_mlp(nn: Any, block_id: str, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    if block_id == "linear":
        out_f = int(config["out_features"])
        lin = nn.Linear(in_f, out_f, bias=bool(config.get("bias", True)))
        act_name = str(config.get("activation", "none"))
        if act_name == "none":
            return lin
        return nn.Sequential(lin, _activation(nn, act_name))
    hidden = int(config["hidden_dim"])
    out_f = int(config["out_features"]) if "out_features" in config else hidden
    act = _activation(nn, str(config.get("activation", "gelu")))
    return nn.Sequential(nn.Linear(in_f, hidden), act, nn.Linear(hidden, out_f))


def _activation(nn: Any, name: str) -> Any:
    table = {
        "relu": nn.ReLU,
        "gelu": nn.GELU,
        "silu": nn.SiLU,
        "mish": nn.Mish,
        "tanh": nn.Tanh,
    }
    cls = table.get(name)
    if cls is None:
        raise ArchitectureValidationError(f"unsupported activation {name!r}")
    return cls()


def _gap1d(nn: Any) -> Any:
    class Pool(nn.Module):  # type: ignore[misc]
        def forward(self, x: Any) -> Any:
            return x.mean(dim=-1)

    return Pool()


def _gap2d(nn: Any) -> Any:
    class Pool(nn.Module):  # type: ignore[misc]
        def forward(self, x: Any) -> Any:
            return x.mean(dim=(-2, -1))

    return Pool()


def _sequence_pool(nn: Any) -> Any:
    class Pool(nn.Module):  # type: ignore[misc]
        def forward(self, x: Any) -> Any:
            return x.mean(dim=1)

    return Pool()


def _vector_to_sequence(nn: Any) -> Any:
    class VectorToSequence(nn.Module):  # type: ignore[misc]
        def forward(self, x: Any) -> Any:
            return x.unsqueeze(1)

    return VectorToSequence()


def _depthwise_conv2d(nn: Any, config: dict[str, Any]) -> Any:
    ch = int(config["in_channels"])
    kernel = int(config["kernel_size"])
    return nn.Conv2d(ch, ch, kernel_size=kernel, padding=kernel // 2, groups=ch)


def _separable_conv2d(nn: Any, config: dict[str, Any]) -> Any:
    in_ch = int(config["in_channels"])
    out_ch = int(config["out_channels"])
    kernel = int(config["kernel_size"])
    depthwise = nn.Conv2d(in_ch, in_ch, kernel_size=kernel, padding=kernel // 2, groups=in_ch)
    pointwise = nn.Conv2d(in_ch, out_ch, kernel_size=1)
    return nn.Sequential(depthwise, pointwise)


def _dilated_conv1d(nn: Any, config: dict[str, Any]) -> Any:
    in_ch = int(config["in_channels"])
    out_ch = int(config["out_channels"])
    kernel = int(config["kernel_size"])
    dilation = int(config.get("dilation", 2))
    padding = ((kernel - 1) * dilation) // 2
    return nn.Conv1d(in_ch, out_ch, kernel_size=kernel, dilation=dilation, padding=padding)


def _grouped_conv2d(nn: Any, config: dict[str, Any]) -> Any:
    in_ch = int(config["in_channels"])
    out_ch = int(config["out_channels"])
    kernel = int(config["kernel_size"])
    groups = int(config.get("groups", 2))
    if in_ch % groups != 0 or out_ch % groups != 0:
        raise ArchitectureValidationError(
            "grouped_conv2d requires in_channels and out_channels divisible by groups",
            details={"in_channels": in_ch, "out_channels": out_ch, "groups": groups},
        )
    return nn.Conv2d(in_ch, out_ch, kernel_size=kernel, padding=kernel // 2, groups=groups)


def _squeeze_excitation(nn: Any, config: dict[str, Any]) -> Any:
    ch = int(config["in_channels"])
    reduction = int(config.get("reduction", 4))
    hidden = max(ch // reduction, 1)

    class SqueezeExcitation(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.fc1 = nn.Linear(ch, hidden)
            self.relu = nn.ReLU()
            self.fc2 = nn.Linear(hidden, ch)
            self.sigmoid = nn.Sigmoid()

        def forward(self, x: Any) -> Any:
            pooled = x.mean(dim=(-2, -1))
            gate = self.sigmoid(self.fc2(self.relu(self.fc1(pooled))))
            return x * gate.unsqueeze(-1).unsqueeze(-1)

    return SqueezeExcitation()


def _self_attention(nn: Any, config: dict[str, Any]) -> Any:
    d_model = int(config.get("d_model", 16))
    nhead = int(config.get("nhead", 2))

    class SelfAttention(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.attn = nn.MultiheadAttention(d_model, nhead, batch_first=True)

        def forward(self, x: Any) -> Any:
            out, _weights = self.attn(x, x, x)
            return out

    return SelfAttention()


def _cross_attention(nn: Any, config: dict[str, Any]) -> Any:
    d_model = int(config.get("d_model", 16))
    nhead = int(config.get("nhead", 2))

    class CrossAttention(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.attn = nn.MultiheadAttention(d_model, nhead, batch_first=True)

        def forward(self, query: Any, context: Any) -> Any:
            out, _weights = self.attn(query, context, context)
            return out

    return CrossAttention()


def _local_attention(nn: Any, config: dict[str, Any]) -> Any:
    d_model = int(config.get("d_model", 16))
    nhead = int(config.get("nhead", 2))
    window = int(config.get("window", 4))

    class LocalAttention(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.attn = nn.MultiheadAttention(d_model, nhead, batch_first=True)
            self.window = window

        def forward(self, x: Any) -> Any:
            batch, length, _dim = x.shape
            pad = (self.window - length % self.window) % self.window
            if pad:
                x = nn.functional.pad(x, (0, 0, 0, pad))
            n_win = x.shape[1] // self.window
            windows = x.reshape(batch * n_win, self.window, _dim)
            out, _weights = self.attn(windows, windows, windows)
            out = out.reshape(batch, n_win * self.window, _dim)
            return out[:, :length, :]

    return LocalAttention()


def _linear_attention(nn: Any, config: dict[str, Any]) -> Any:
    d_model = int(config.get("d_model", 16))
    nhead = int(config.get("nhead", 2))
    if nhead < 1 or d_model % nhead != 0:
        raise ArchitectureValidationError(
            f"linear_attention requires d_model % nhead == 0 (d_model={d_model}, nhead={nhead})"
        )
    head_dim = d_model // nhead

    class LinearAttention(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.nhead = nhead
            self.head_dim = head_dim
            self.q = nn.Linear(d_model, d_model)
            self.k = nn.Linear(d_model, d_model)
            self.v = nn.Linear(d_model, d_model)
            self.out = nn.Linear(d_model, d_model)

        def _heads(self, tensor: Any) -> Any:
            batch, length, _dim = tensor.shape
            return tensor.view(batch, length, self.nhead, self.head_dim).transpose(1, 2)

        def forward(self, x: Any) -> Any:
            query = self._heads(nn.functional.elu(self.q(x)) + 1.0)
            key = self._heads(nn.functional.elu(self.k(x)) + 1.0)
            value = self._heads(self.v(x))
            kv = key.transpose(-2, -1) @ value
            out = query @ kv
            denom = query @ key.sum(dim=2).unsqueeze(-1)
            out = out / denom.clamp(min=1e-6)
            batch, _heads, length, _dim = out.shape
            merged = out.transpose(1, 2).contiguous().view(batch, length, d_model)
            return self.out(merged)

    return LinearAttention()


def _neural_ode(nn: Any, config: dict[str, Any]) -> Any:
    dim = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 16))
    steps = int(config.get("steps", 4))

    class EulerODE(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.net = nn.Sequential(nn.Linear(dim, hidden), nn.Tanh(), nn.Linear(hidden, dim))
            self.steps = steps

        def forward(self, x: Any) -> Any:
            hidden_state = x
            dt = 1.0 / float(self.steps)
            for _ in range(self.steps):
                hidden_state = hidden_state + dt * self.net(hidden_state)
            return hidden_state

    return EulerODE()


def _deeponet(nn: Any, config: dict[str, Any]) -> Any:
    branch_dim = int(config.get("branch_dim", 8))
    trunk_dim = int(config.get("trunk_dim", 8))
    hidden = int(config.get("hidden_dim", 16))
    rank = int(config.get("p", 8))

    class DeepONet(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.branch = nn.Sequential(
                nn.Linear(branch_dim, hidden), nn.Tanh(), nn.Linear(hidden, rank)
            )
            self.trunk = nn.Sequential(
                nn.Linear(trunk_dim, hidden), nn.Tanh(), nn.Linear(hidden, rank)
            )

        def forward(self, branch: Any, trunk: Any) -> Any:
            return (self.branch(branch) * self.trunk(trunk)).sum(dim=-1, keepdim=True)

    return DeepONet()


def _pinn_motif(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 16))
    out_f = int(config.get("out_features", 1))
    n_layers = int(config.get("n_layers", 2))
    layers: list[Any] = [nn.Linear(in_f, hidden), nn.Tanh()]
    for _ in range(max(n_layers - 1, 0)):
        layers.extend([nn.Linear(hidden, hidden), nn.Tanh()])
    layers.append(nn.Linear(hidden, out_f))
    return nn.Sequential(*layers)


def _swiglu(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 128))

    class SwiGLU(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.proj = nn.Linear(in_f, 2 * hidden)
            self.silu = nn.SiLU()
            self.out = nn.Linear(hidden, in_f)

        def forward(self, x: Any) -> Any:
            a, b = self.proj(x).chunk(2, dim=-1)
            return self.out(a * self.silu(b))

    return SwiGLU()


def _residual_mlp(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 16))

    class ResidualMLP(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.block = nn.Sequential(nn.Linear(in_f, hidden), nn.GELU(), nn.Linear(hidden, in_f))

        def forward(self, x: Any) -> Any:
            return x + self.block(x)

    return ResidualMLP()


def _residual_gated(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))

    class ResidualGated(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.transform = nn.Sequential(nn.Linear(in_f, in_f), nn.GELU())
            self.gate = nn.Sequential(nn.Linear(in_f, in_f), nn.Sigmoid())

        def forward(self, x: Any) -> Any:
            gate = self.gate(x)
            return x + gate * self.transform(x)

    return ResidualGated()


def _highway(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))

    class Highway(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.transform = nn.Sequential(nn.Linear(in_f, in_f), nn.ReLU())
            self.gate = nn.Sequential(nn.Linear(in_f, in_f), nn.Sigmoid())

        def forward(self, x: Any) -> Any:
            t = self.gate(x)
            return t * self.transform(x) + (1 - t) * x

    return Highway()


def _geglu(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("in_features", 8))
    hidden = int(config.get("hidden_dim", 16))

    class GEGLU(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.proj = nn.Linear(in_f, 2 * hidden)
            self.gelu = nn.GELU()
            self.out = nn.Linear(hidden, in_f)

        def forward(self, x: Any) -> Any:
            a, b = self.proj(x).chunk(2, dim=-1)
            return self.out(a * self.gelu(b))

    return GEGLU()


def _tcn(nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config.get("input_size", 8))
    hidden = int(config.get("hidden_dim", 32))
    n_layers = int(config.get("n_layers", 1))
    kernel_size = int(config.get("kernel_size", 3))

    class CausalBlock(nn.Module):  # type: ignore[misc]
        def __init__(self, c_in: int, c_out: int, dilation: int) -> None:
            super().__init__()
            self._padding = (kernel_size - 1) * dilation
            self.conv = nn.Conv1d(
                c_in, c_out, kernel_size, padding=self._padding, dilation=dilation
            )
            self.act = nn.ReLU()
            self.residual = (
                nn.Conv1d(c_in, c_out, kernel_size=1) if c_in != c_out else nn.Identity()
            )

        def forward(self, x: Any) -> Any:
            out = self.conv(x)
            if self._padding:
                out = out[..., : -self._padding]
            return self.act(out) + self.residual(x)

    class TCN(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            blocks = []
            c_in = in_f
            for i in range(n_layers):
                blocks.append(CausalBlock(c_in, hidden, dilation=2**i))
                c_in = hidden
            self.blocks = nn.ModuleList(blocks)

        def forward(self, x: Any) -> Any:
            h = x.transpose(1, 2)
            for block in self.blocks:
                h = block(h)
            return h.transpose(1, 2)

    return TCN()


def _graph_pool(nn: Any, block_id: str) -> Any:
    if block_id == "graph_global_pool":

        class GraphGlobalPool(nn.Module):  # type: ignore[misc]
            def forward(self, x: Any) -> Any:
                return x.mean(dim=0, keepdim=True)

        return GraphGlobalPool()
    return nn.Identity()


def _gnn_block(torch: Any, nn: Any, block_id: str, config: dict[str, Any]) -> Any:
    from oec.kernel.neural.gnn import _normalize_adj, build_gnn

    hidden = int(config["hidden_dim"])
    in_dim = int(config.get("input_size", hidden))
    n_layers = int(config["n_layers"])
    heads = int(config.get("heads", 2))
    inner = build_gnn(
        block_id,  # type: ignore[arg-type]
        in_dim,
        hidden=hidden,
        n_layers=n_layers,
        output_dim=hidden,
        heads=heads,
    )

    class GnnBlock(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.inner = inner

        def forward(self, features: Any, edge_index: Any) -> Any:
            if block_id == "gat":
                return self.inner(features, edge_index)
            n = features.shape[0]
            adj = _normalize_adj(torch, edge_index, n)
            return self.inner(features, edge_index, adj)

    return GnnBlock()


def _bspline_basis(torch: Any, x: Any, grid: Any, degree: int) -> Any:
    x = x.unsqueeze(-1)
    bases = ((x >= grid[:-1]) & (x < grid[1:])).to(x.dtype)
    for k in range(1, degree + 1):
        left_den = grid[k:-1] - grid[: -(k + 1)]
        right_den = grid[k + 1 :] - grid[1:-k]
        left = (x - grid[: -(k + 1)]) / left_den * bases[..., :-1]
        right = (grid[k + 1 :] - x) / right_den * bases[..., 1:]
        bases = left + right
    return bases


def _kan_module(torch: Any, nn: Any, config: dict[str, Any]) -> Any:
    in_f = int(config["in_features"])
    out_f = int(config["out_features"])
    basis = str(config.get("basis", "bspline"))
    grid_size = int(config.get("grid_size", 8))
    degree = 3
    if basis not in {"bspline", "rbf"}:
        raise ArchitectureValidationError(f"unknown KAN basis {basis!r}")

    class KANLinear(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            if basis == "bspline":
                h = 2.0 / grid_size
                grid = torch.arange(-degree, grid_size + degree + 1, dtype=torch.float32) * h - 1.0
                self.register_buffer("grid", grid)
                n_basis = grid_size + degree
            else:
                centers = torch.linspace(-1.0, 1.0, grid_size)
                self.register_buffer("centers", centers)
                n_basis = grid_size
            self._sigma = 2.0 / grid_size
            self.weight = nn.Parameter(torch.randn(in_f, n_basis, out_f) * 0.1)
            self.base = nn.Linear(in_f, out_f)

        def _basis(self, x: Any) -> Any:
            xc = torch.clamp(x, -1.0, 1.0)
            if basis == "bspline":
                return _bspline_basis(torch, xc, self.grid, degree)
            diff = xc.unsqueeze(-1) - self.centers
            return torch.exp(-(diff**2) / (2 * self._sigma**2))

        def forward(self, x: Any) -> Any:
            b = self._basis(x)
            spline_out = torch.einsum("bik,iko->bo", b, self.weight)
            return spline_out + self.base(torch.tanh(x))

    return KANLinear()


def _fno_1d(torch: Any, nn: Any, config: dict[str, Any]) -> Any:
    in_ch = int(config.get("in_channels", 1))
    out_ch = int(config.get("out_channels", 1))
    modes = int(config.get("modes", 4))

    class FNO1D(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            scale = 1.0 / (in_ch * out_ch)
            self.weight = nn.Parameter(
                scale * torch.randn(in_ch, out_ch, modes, dtype=torch.cfloat)
            )
            self.skip = nn.Conv1d(in_ch, out_ch, kernel_size=1)

        def forward(self, x: Any) -> Any:
            if x.dim() != 3:
                raise ArchitectureValidationError(
                    f"fno expects rank-3 input (N, C, L); got rank {x.dim()}",
                    details={"rank": x.dim()},
                )
            x_ft = torch.fft.rfft(x, dim=-1)
            m = min(modes, x_ft.shape[-1])
            out_ft = torch.zeros(
                x.shape[0], out_ch, x_ft.shape[-1], dtype=torch.cfloat, device=x.device
            )
            out_ft[:, :, :m] = torch.einsum("bim,iom->bom", x_ft[:, :, :m], self.weight[:, :, :m])
            out = torch.fft.irfft(out_ft, n=x.shape[-1], dim=-1)
            return out + self.skip(x)

    return FNO1D()


def _fno_2d(torch: Any, nn: Any, config: dict[str, Any]) -> Any:
    in_ch = int(config.get("in_channels", 1))
    out_ch = int(config.get("out_channels", 1))
    modes = int(config.get("modes", 4))

    class FNO2D(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            scale = 1.0 / (in_ch * out_ch)
            self.weight = nn.Parameter(
                scale * torch.randn(in_ch, out_ch, modes, modes, dtype=torch.cfloat)
            )
            self.skip = nn.Conv2d(in_ch, out_ch, kernel_size=1)

        def forward(self, x: Any) -> Any:
            if x.dim() != 4:
                raise ArchitectureValidationError(
                    f"fno_2d expects rank-4 input (N, C, H, W); got rank {x.dim()}",
                    details={"rank": x.dim()},
                )
            x_ft = torch.fft.rfft2(x, dim=(-2, -1))
            mh = min(modes, x_ft.shape[-2])
            mw = min(modes, x_ft.shape[-1])
            out_ft = torch.zeros(
                x.shape[0],
                out_ch,
                x_ft.shape[-2],
                x_ft.shape[-1],
                dtype=torch.cfloat,
                device=x.device,
            )
            out_ft[:, :, :mh, :mw] = torch.einsum(
                "bihw,iohw->bohw", x_ft[:, :, :mh, :mw], self.weight[:, :, :mh, :mw]
            )
            out = torch.fft.irfft2(out_ft, s=x.shape[-2:], dim=(-2, -1))
            return out + self.skip(x)

    return FNO2D()


def _invoke_unary(module: Any, x: Any) -> Any:
    out = module(x)
    if isinstance(out, tuple):
        out = out[0]
    return out


def _graph_sequential(
    nn: Any,
    order: list[str],
    modules: dict[str, Any],
    edges_by_target: dict[str, list[tuple[str, str, str]]],
    graph_node_ids: set[str],
) -> Any:
    class GraphSequential(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self._order = list(order)
            self._edges_by_target = edges_by_target
            self._graph_node_ids = set(graph_node_ids)
            for node_id, module in modules.items():
                self.add_module(node_id, module)

        def forward(self, x: Any) -> Any:
            edge_index = None
            if isinstance(x, Mapping):
                features = x["features"]
                edge_index = x.get("edge_index")
            elif isinstance(x, tuple | list) and len(x) == 2:
                features, edge_index = x
            else:
                features = x

            outputs: dict[str, Any] = {}
            for node_id in self._order:
                module = getattr(self, node_id)
                incoming = self._edges_by_target.get(node_id, [])
                if node_id in self._graph_node_ids:
                    if edge_index is None:
                        raise ArchitectureValidationError(
                            f"graph block {node_id!r} requires edge_index input"
                        )
                    if not incoming:
                        node_features = features
                    elif len(incoming) == 1:
                        src_id, _source_port, _target_port = incoming[0]
                        node_features = outputs[src_id]
                    else:
                        raise ArchitectureValidationError(
                            f"graph block {node_id!r} does not support multi-port joins"
                        )
                    result = module(node_features, edge_index)
                elif not incoming:
                    result = _invoke_unary(module, features)
                elif len(incoming) == 1:
                    src_id, _source_port, _target_port = incoming[0]
                    result = _invoke_unary(module, outputs[src_id])
                else:
                    ports = {
                        target_port: outputs[src_id]
                        for src_id, _source_port, target_port in incoming
                    }
                    result = module(**ports)
                outputs[node_id] = result
            return outputs[self._order[-1]]

    return GraphSequential()
