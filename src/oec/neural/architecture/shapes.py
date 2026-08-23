"""Closed per-block feature-dim signatures (ADR 0047). Core-safe, no torch.

An edge is dimensionally proven when both endpoints declare a feature-dim
key and the integers match. Adapters without a dim key (flatten, pools)
are runtime-shaped: they do not prove or refute a number. A declared dim
on one side and a missing dim on the other is unprovable and fails closed
when the missing side is a block that *has* a signature (miswired port).
"""

from __future__ import annotations

from collections.abc import Mapping

from oec.neural.architecture.graph import ArchitectureGraph, EdgeGene, NodeGene
from oec.neural.architecture.registry import BlockRegistry

# block_id -> config key for the tensor arriving at the default "in" port
INPUT_DIM_KEY: dict[str, str] = {
    "linear": "in_features",
    "mlp": "in_features",
    "residual_mlp": "in_features",
    "swiglu": "in_features",
    "kan": "in_features",
    "encoder": "in_features",
    "decoder": "in_features",
    "geglu": "in_features",
    "residual_gated": "in_features",
    "highway": "in_features",
    "neural_ode": "in_features",
    "pinn_motif": "in_features",
    "conv1d": "in_channels",
    "conv2d": "in_channels",
    "depthwise_conv2d": "in_channels",
    "separable_conv2d": "in_channels",
    "dilated_conv1d": "in_channels",
    "grouped_conv2d": "in_channels",
    "squeeze_excitation": "in_channels",
    "fno": "in_channels",
    "fno_2d": "in_channels",
    "lstm": "input_size",
    "gru": "input_size",
    "tcn": "input_size",
    "gcn": "input_size",
    "graphsage": "input_size",
    "gat": "input_size",
    "self_attention": "d_model",
    "transformer_encoder": "d_model",
    "cross_attention": "d_model",
    "local_attention": "d_model",
    "linear_attention": "d_model",
}

# block_id -> config key for the tensor leaving port "out"
OUTPUT_DIM_KEY: dict[str, str] = {
    "linear": "out_features",
    "mlp": "out_features",
    "kan": "out_features",
    "encoder": "out_features",
    "decoder": "out_features",
    "pinn_motif": "out_features",
    "residual_mlp": "in_features",
    "swiglu": "in_features",
    "geglu": "in_features",
    "residual_gated": "in_features",
    "highway": "in_features",
    "neural_ode": "in_features",
    "conv1d": "out_channels",
    "conv2d": "out_channels",
    "depthwise_conv2d": "in_channels",
    "separable_conv2d": "out_channels",
    "dilated_conv1d": "out_channels",
    "grouped_conv2d": "out_channels",
    "squeeze_excitation": "in_channels",
    "fno": "out_channels",
    "fno_2d": "out_channels",
    "lstm": "hidden_dim",
    "gru": "hidden_dim",
    "tcn": "hidden_dim",
    "gcn": "hidden_dim",
    "graphsage": "hidden_dim",
    "gat": "hidden_dim",
    "self_attention": "d_model",
    "transformer_encoder": "d_model",
    "cross_attention": "d_model",
    "local_attention": "d_model",
    "linear_attention": "d_model",
}

_NAMED_INPUT_DIM_KEY: dict[tuple[str, str], str] = {
    ("cross_attention", "query"): "d_model",
    ("cross_attention", "context"): "d_model",
    ("deeponet", "branch"): "branch_dim",
    ("deeponet", "trunk"): "trunk_dim",
}


def input_dim_key(block_id: str, port: str = "in") -> str | None:
    named = _NAMED_INPUT_DIM_KEY.get((block_id, port))
    if named is not None:
        return named
    if port in {"in", "query", "context", "branch", "trunk"}:
        return INPUT_DIM_KEY.get(block_id)
    return None


def output_dim_key(block_id: str, port: str = "out") -> str | None:
    if port != "out":
        return None
    return OUTPUT_DIM_KEY.get(block_id)


def _int_config(config: Mapping[str, object], key: str | None) -> int | None:
    if key is None or key not in config:
        return None
    value = config[key]
    if type(value) is bool or type(value) is not int:
        return None
    return int(value)


def edge_dim_error(
    source: NodeGene,
    target: NodeGene,
    edge: EdgeGene,
) -> str | None:
    out_key = output_dim_key(source.block_id, edge.source_port)
    in_key = input_dim_key(target.block_id, edge.target_port)
    out_dim = _int_config(source.config, out_key)
    in_dim = _int_config(target.config, in_key)
    if out_key is None and in_key is None:
        return None
    if out_key is None or in_key is None:
        missing = "source output" if out_key is None else "target input"
        return (
            f"unprovable dim on {edge.source}->{edge.target} "
            f"(port {edge.target_port}): {missing} has no feature-dim signature"
        )
    if out_dim is None or in_dim is None:
        return (
            f"unprovable dim on {edge.source}->{edge.target}: "
            f"{out_key if out_dim is None else in_key} is missing"
        )
    if out_dim != in_dim:
        return (
            f"dim mismatch on {edge.source}->{edge.target}: "
            f"{source.block_id}.{out_key}={out_dim} vs "
            f"{target.block_id}.{in_key}={in_dim}"
        )
    return None


def graph_dim_errors(graph: ArchitectureGraph, registry: BlockRegistry) -> list[str]:
    del registry
    node_map = {node.id: node for node in graph.nodes}
    errors: list[str] = []
    for edge in graph.edges:
        source = node_map.get(edge.source)
        target = node_map.get(edge.target)
        if source is None or target is None:
            continue
        message = edge_dim_error(source, target, edge)
        if message is not None:
            errors.append(message)
    return errors


def propagate_output_width(
    nodes: tuple[NodeGene, ...],
    edges: tuple[EdgeGene, ...],
    source_id: str,
    width: int,
) -> list[NodeGene]:
    """Set each successor's input-dim key to ``width``. Idempotent copy."""
    node_map = {node.id: node for node in nodes}
    for edge in edges:
        if edge.source != source_id:
            continue
        target = node_map.get(edge.target)
        if target is None:
            continue
        key = input_dim_key(target.block_id, edge.target_port)
        if key is None:
            continue
        cfg = dict(target.config)
        cfg[key] = width
        node_map[target.id] = NodeGene(id=target.id, block_id=target.block_id, config=cfg)
    return [node_map[node.id] for node in nodes]
