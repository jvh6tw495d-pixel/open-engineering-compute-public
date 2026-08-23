"""Closed per-block feature-dim signatures (ADR 0047). Core-safe, no torch.

An edge is dimensionally proven when both endpoints declare a feature-dim
key and the integers match. Feature-dim-preserving adapters (global pools,
sequence pool, graph pool, vector_to_sequence) carry that integer across
to the next signed block — so ``conv → pool → mlp`` is proven.
``flatten`` is not preserving (output is C×spatial); those edges stay
runtime-shaped. A declared key whose config integer is missing still fails.
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
    "glu": "in_features",
    "hybrid_kan": "in_features",
    "lif_spike": "features",
    "residual_stack": "in_features",
    "bottleneck": "in_features",
    "fusion": "in_features",
    "encoder_decoder": "in_features",
    "vae": "in_features",
    "gan_generator": "in_features",
    "gan_discriminator": "in_features",
    "moe": "in_features",
    "siamese": "in_features",
    "diffusion_denoiser": "in_features",
    "residual_conv": "in_channels",
    "conv3d": "in_channels",
    "inception": "in_channels",
    "dense_block": "in_channels",
    "message_passing_stack": "input_size",
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
    "glu": "in_features",
    "hybrid_kan": "out_features",
    "lif_spike": "features",
    "residual_stack": "in_features",
    "bottleneck": "in_features",
    "fusion": "out_features",
    "encoder_decoder": "out_features",
    "vae": "out_features",
    "gan_generator": "out_features",
    "gan_discriminator": "out_features",
    "moe": "out_features",
    "siamese": "out_features",
    "diffusion_denoiser": "in_features",
    "residual_conv": "out_channels",
    "conv3d": "out_channels",
    "inception": "out_channels",
    "dense_block": "out_channels",
    "message_passing_stack": "hidden_dim",
}

_NAMED_INPUT_DIM_KEY: dict[tuple[str, str], str] = {
    ("cross_attention", "query"): "d_model",
    ("cross_attention", "context"): "d_model",
    ("deeponet", "branch"): "branch_dim",
    ("deeponet", "trunk"): "trunk_dim",
    ("fusion", "a"): "in_features",
    ("fusion", "b"): "in_features",
    ("siamese", "left"): "in_features",
    ("siamese", "right"): "in_features",
}

# Adapters that keep the feature/channel/d_model integer while changing rank.
# flatten is excluded: it mixes channels with spatial size.
PRESERVES_FEATURE_DIM: frozenset[str] = frozenset(
    {
        "global_avg_pool_1d",
        "global_avg_pool_2d",
        "global_avg_pool_3d",
        "sequence_pool",
        "vector_to_sequence",
        "graph_global_pool",
        "graph_embedding_to_vector",
    }
)


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
    if out_key is None or in_key is None:
        # Adapter / pool / flatten: runtime-shaped. No integer to prove.
        return None
    out_dim = _int_config(source.config, out_key)
    in_dim = _int_config(target.config, in_key)
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


def _outgoing(edges: tuple[EdgeGene, ...]) -> dict[str, list[EdgeGene]]:
    mapping: dict[str, list[EdgeGene]] = {}
    for edge in edges:
        mapping.setdefault(edge.source, []).append(edge)
    return mapping


def first_signed_successor(
    node_map: dict[str, NodeGene],
    outgoing: dict[str, list[EdgeGene]],
    start_id: str,
    *,
    seen: set[str] | None = None,
) -> tuple[NodeGene, str] | None:
    """Next node with an input-dim key, walking unique preserving adapters."""
    visited = seen if seen is not None else set()
    if start_id in visited:
        return None
    visited.add(start_id)
    edges = outgoing.get(start_id, [])
    if len(edges) != 1:
        return None
    edge = edges[0]
    target = node_map.get(edge.target)
    if target is None:
        return None
    key = input_dim_key(target.block_id, edge.target_port)
    if key is not None:
        return target, key
    if target.block_id not in PRESERVES_FEATURE_DIM:
        return None
    return first_signed_successor(node_map, outgoing, target.id, seen=visited)


def graph_dim_errors(graph: ArchitectureGraph, registry: BlockRegistry) -> list[str]:
    del registry
    node_map = {node.id: node for node in graph.nodes}
    outgoing = _outgoing(graph.edges)
    errors: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()
    for edge in graph.edges:
        source = node_map.get(edge.source)
        target = node_map.get(edge.target)
        if source is None or target is None:
            continue
        message = edge_dim_error(source, target, edge)
        if message is not None:
            errors.append(message)
            seen_pairs.add((source.id, target.id))
        out_key = output_dim_key(source.block_id, edge.source_port)
        out_dim = _int_config(source.config, out_key)
        if out_dim is None:
            continue
        signed = first_signed_successor(node_map, outgoing, source.id)
        if signed is None:
            continue
        dest, in_key = signed
        if (source.id, dest.id) in seen_pairs:
            continue
        in_dim = _int_config(dest.config, in_key)
        if in_dim is None:
            errors.append(f"unprovable dim on {source.id}~>{dest.id}: {in_key} is missing")
            continue
        if out_dim != in_dim:
            errors.append(
                f"dim mismatch on {source.id}~>{dest.id} (via preserving adapter): "
                f"{source.block_id}.{out_key}={out_dim} vs "
                f"{dest.block_id}.{in_key}={in_dim}"
            )
        seen_pairs.add((source.id, dest.id))
    return errors


def propagate_output_width(
    nodes: tuple[NodeGene, ...],
    edges: tuple[EdgeGene, ...],
    source_id: str,
    width: int,
) -> list[NodeGene]:
    """Set each successor's input-dim key to ``width``, skipping preserving adapters."""
    node_map = {node.id: node for node in nodes}
    outgoing = _outgoing(edges)
    for edge in edges:
        if edge.source != source_id:
            continue
        target = node_map.get(edge.target)
        if target is None:
            continue
        key = input_dim_key(target.block_id, edge.target_port)
        dest = target
        if key is None:
            signed = first_signed_successor(node_map, outgoing, source_id)
            if signed is None:
                continue
            dest, key = signed
        cfg = dict(dest.config)
        cfg[key] = width
        node_map[dest.id] = NodeGene(id=dest.id, block_id=dest.block_id, config=cfg)
    return [node_map[node.id] for node in nodes]
