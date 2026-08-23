"""Build a torch.nn.Module from ArchitectureGraph (ADR 0047 wave A7).

Torch is imported only inside ``build_architecture``. The architecture IR
package stays core-safe.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.neural.architecture import default_registry
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.graph import ArchitectureGraph
from oec.neural.architecture.registry import BlockRegistry

_UNSUPPORTED = frozenset(
    {
        "kan",
        "gcn",
        "graphsage",
        "gat",
        "swiglu",
        "residual_mlp",
        "self_attention",
        "tcn",
        "vector_to_sequence",
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
    """Materialize a sequential DAG. Branched graphs and KAN/GNN fail closed."""
    if backend != "torch":
        raise ValueError(f"unsupported architecture backend {backend!r}")
    registry = registry or default_registry
    report = graph.validate_graph(registry)
    if not report.valid:
        raise ArchitectureValidationError("; ".join(report.errors))
    torch, nn = _require_torch()
    order = _topo_order(graph)
    modules: dict[str, Any] = {}
    for node_id in order:
        node = next(n for n in graph.nodes if n.id == node_id)
        if node.block_id in _UNSUPPORTED:
            raise ArchitectureValidationError(
                f"block {node.block_id!r} has no torch builder in A7 "
                f"(missing backend or not in this wave)"
            )
        modules[node_id] = _build_block(nn, node.block_id, dict(node.config))
    return _graph_sequential(nn, graph, order, modules)


def _topo_order(graph: ArchitectureGraph) -> list[str]:
    ids = [node.id for node in graph.nodes]
    indegree = {node_id: 0 for node_id in ids}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in ids}
    incoming: dict[str, list[str]] = {node_id: [] for node_id in ids}
    for edge in graph.edges:
        outgoing[edge.source].append(edge.target)
        incoming[edge.target].append(edge.source)
        indegree[edge.target] += 1
    if any(len(srcs) > 1 for srcs in incoming.values()):
        raise ArchitectureValidationError("branched graphs are not supported in A7")
    queue = [node_id for node_id, deg in indegree.items() if deg == 0]
    order: list[str] = []
    while queue:
        current = queue.pop(0)
        order.append(current)
        for nxt in outgoing[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(ids):
        raise ArchitectureValidationError("architecture graph is not a valid DAG")
    return order


def _build_block(nn: Any, block_id: str, config: dict[str, Any]) -> Any:
    if block_id in {"linear", "mlp"}:
        in_f = int(config.get("in_features") or config.get("input_dim") or 8)
        hidden = int(config.get("hidden_dim") or config.get("out_features") or 16)
        out_f = int(config.get("out_features") or config.get("output_dim") or hidden)
        if block_id == "linear":
            return nn.Linear(in_f, int(config.get("out_features") or out_f))
        return nn.Sequential(nn.Linear(in_f, hidden), nn.GELU(), nn.Linear(hidden, out_f))
    if block_id in {"encoder", "decoder"}:
        in_f = int(config.get("in_features") or 8)
        out_f = int(config.get("out_features") or 4)
        return nn.Sequential(nn.Linear(in_f, out_f), nn.GELU())
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
            int(config.get("in_channels") or 1),
            int(config.get("out_channels") or 8),
            kernel_size=int(config.get("kernel_size") or 3),
            padding=1,
        )
    if block_id == "conv2d":
        return nn.Conv2d(
            int(config.get("in_channels") or 1),
            int(config.get("out_channels") or 8),
            kernel_size=int(config.get("kernel_size") or 3),
            padding=1,
        )
    if block_id in {"lstm", "gru"}:
        hidden = int(config.get("hidden_dim") or 16)
        cls = nn.LSTM if block_id == "lstm" else nn.GRU
        return cls(int(config.get("input_size") or 8), hidden, batch_first=True)
    if block_id == "transformer_encoder":
        d_model = int(config.get("d_model") or 16)
        layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=int(config.get("nhead") or 2),
            dim_feedforward=int(config.get("dim_feedforward") or 32),
            batch_first=True,
        )
        return nn.TransformerEncoder(layer, num_layers=int(config.get("num_layers") or 1))
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
    graph: ArchitectureGraph,
    order: list[str],
    modules: dict[str, Any],
) -> Any:
    class GraphSequential(nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self._order = list(order)
            incoming: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
            for edge in graph.edges:
                incoming[edge.target].append(edge.source)
            self._incoming = incoming
            for node_id, module in modules.items():
                self.add_module(node_id, module)

        def forward(self, x: Any) -> Any:
            values: dict[str, Any] = {}
            for node_id in self._order:
                srcs = self._incoming[node_id]
                inp = x if not srcs else values[srcs[0]]
                module = getattr(self, node_id)
                out = module(inp) if not isinstance(module, tuple) else module[0](inp)
                if isinstance(out, tuple):
                    out = out[0]
                values[node_id] = out
            return values[self._order[-1]]

    return GraphSequential()
