"""Closed backend ids for Architecture IR manifests and A7 builders.

Core-safe — no torch import. Keep in sync with ``architecture_build``.
"""

from __future__ import annotations

KNOWN_MANIFEST_BACKENDS = frozenset({"torch"})

# Blocks A7 can materialize for backend="torch". Catalog entries not in this
# set (local_attention, linear_attention, neural_ode, deeponet, pinn_motif)
# remain fail-closed and must not receive a torch manifest.
TORCH_BUILDABLE_BLOCK_IDS = frozenset(
    {
        "linear",
        "mlp",
        "encoder",
        "decoder",
        "flatten",
        "global_avg_pool_1d",
        "global_avg_pool_2d",
        "sequence_pool",
        "vector_to_sequence",
        "conv1d",
        "conv2d",
        "depthwise_conv2d",
        "separable_conv2d",
        "dilated_conv1d",
        "grouped_conv2d",
        "squeeze_excitation",
        "lstm",
        "gru",
        "tcn",
        "transformer_encoder",
        "self_attention",
        "cross_attention",
        "swiglu",
        "residual_mlp",
        "residual_gated",
        "highway",
        "geglu",
        "kan",
        "fno",
        "fno_2d",
        "gcn",
        "graphsage",
        "gat",
        "graph_global_pool",
        "graph_embedding_to_vector",
    }
)
