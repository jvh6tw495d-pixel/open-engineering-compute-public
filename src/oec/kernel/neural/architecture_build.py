"""Build a torch.nn.Module from ArchitectureGraph (ADR 0047 wave A7).

Torch is imported only inside ``build_architecture``. The architecture IR
package stays core-safe. A7 materializes a strict linear chain only.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.neural.architecture import default_registry
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.graph import ArchitectureGraph
from oec.neural.architecture.registry import BlockRegistry

_TORCH_BUILDERS = frozenset(
    {
        "linear",
        "mlp",
        "encoder",
        "decoder",
        "flatten",
        "global_avg_pool_1d",
        "global_avg_pool_2d",
        "sequence_pool",
        "conv1d",
        "conv2d",
        "lstm",
        "gru",
        "transformer_encoder",
        "graph_global_pool",
        "graph_embedding_to_vector",
    }
)


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
    """Materialize a strict linear chain. Forks, joins, and KAN/GNN fail closed."""
    if backend != "torch":
        raise ValueError(f"unsupported architecture backend {backend!r}")
    registry = registry or default_registry
    report = graph.validate_graph(registry)
    if not report.valid:
        raise ArchitectureValidationError("; ".join(report.errors))
    order = _require_linear_chain(graph)
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
    for node_id in order:
        node = node_map[node_id]
        spec = registry.get(node.block_id)
        modules[node_id] = _build_block(nn, node.block_id, spec.validate_config(node.config))
    return _graph_sequential(nn, order, modules)


def _require_linear_chain(graph: ArchitectureGraph) -> list[str]:
    ids = [node.id for node in graph.nodes]
    if not ids:
        raise ArchitectureValidationError("empty architecture graph is not supported in A7")
    incoming: dict[str, list[str]] = {node_id: [] for node_id in ids}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in ids}
    for edge in graph.edges:
        if edge.source not in incoming or edge.target not in incoming:
            raise ArchitectureValidationError(
                f"unknown edge {edge.source}->{edge.target} in A7 linear chain"
            )
        outgoing[edge.source].append(edge.target)
        incoming[edge.target].append(edge.source)
    if any(len(srcs) > 1 for srcs in incoming.values()):
        raise ArchitectureValidationError("branched graphs are not supported in A7")
    if any(len(dsts) > 1 for dsts in outgoing.values()):
        raise ArchitectureValidationError("forked graphs are not supported in A7")
    if len(graph.edges) != len(ids) - 1:
        raise ArchitectureValidationError("architecture graph is not a linear chain in A7")
    roots = [node_id for node_id, srcs in incoming.items() if not srcs]
    sinks = [node_id for node_id, dsts in outgoing.items() if not dsts]
    if len(roots) != 1 or len(sinks) != 1:
        raise ArchitectureValidationError("architecture graph is not a linear chain in A7")
    order: list[str] = []
    current = roots[0]
    seen: set[str] = set()
    while True:
        if current in seen:
            raise ArchitectureValidationError("architecture graph is not a valid DAG")
        seen.add(current)
        order.append(current)
        nxts = outgoing[current]
        if not nxts:
            break
        current = nxts[0]
    if len(order) != len(ids):
        raise ArchitectureValidationError("disconnected architecture graph is not supported in A7")
    return order


def _build_block(nn: Any, block_id: str, config: dict[str, Any]) -> Any:
    if block_id in {"linear", "mlp"}:
        in_f = int(config["in_features"])
        hidden = int(config["hidden_dim"]) if block_id == "mlp" else in_f
        out_f = int(config["out_features"]) if "out_features" in config else hidden
        if block_id == "linear":
            return nn.Linear(in_f, out_f, bias=bool(config.get("bias", True)))
        return nn.Sequential(nn.Linear(in_f, hidden), nn.GELU(), nn.Linear(hidden, out_f))
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
    if block_id in {"lstm", "gru"}:
        hidden = int(config["hidden_dim"])
        cls = nn.LSTM if block_id == "lstm" else nn.GRU
        return cls(int(config["input_size"]), hidden, batch_first=True)
    if block_id == "transformer_encoder":
        layer = nn.TransformerEncoderLayer(
            d_model=int(config["d_model"]),
            nhead=int(config["nhead"]),
            dim_feedforward=int(config["dim_feedforward"]),
            batch_first=True,
        )
        return nn.TransformerEncoder(layer, num_layers=int(config["num_layers"]))
    if block_id in {"graph_global_pool", "graph_embedding_to_vector"}:
        return nn.Identity()
    raise ArchitectureValidationError(f"no torch builder for block {block_id!r}")


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


def _graph_sequential(
    nn: Any,
    order: list[str],
    modules: dict[str, Any],
) -> Any:
    class GraphSequential(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self._order = list(order)
            for node_id, module in modules.items():
                self.add_module(node_id, module)

        def forward(self, x: Any) -> Any:
            current = x
            for node_id in self._order:
                module = getattr(self, node_id)
                out = module(current) if not isinstance(module, tuple) else module[0](current)
                if isinstance(out, tuple):
                    out = out[0]
                current = out
            return current

    return GraphSequential()
