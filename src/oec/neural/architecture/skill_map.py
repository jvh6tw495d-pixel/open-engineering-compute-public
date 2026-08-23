"""Map existing neural skill ids onto ArchitectureGraph (ADR 0047 wave A5).

Declarative only — does not train or change skill numerics.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from oec.neural.architecture.errors import UnknownBlockError
from oec.neural.architecture.graph import ArchitectureGraph, EdgeGene, NodeGene


def graph_for_skill(skill_id: str, inputs: dict[str, Any] | None = None) -> ArchitectureGraph:
    """Return a governed graph for a known neural skill. Unknown ids fail closed."""
    del inputs  # reserved for A7 builders; A5 is structural
    key = str(skill_id).strip()
    builder = _SKILL_GRAPHS.get(key)
    if builder is None:
        raise UnknownBlockError(f"no architecture mapping for skill {key!r}")
    graph: ArchitectureGraph = builder()
    return graph


def _chain(nodes: tuple[NodeGene, ...]) -> ArchitectureGraph:
    edges = tuple(
        EdgeGene(source=nodes[i].id, target=nodes[i + 1].id) for i in range(len(nodes) - 1)
    )
    return ArchitectureGraph(nodes=nodes, edges=edges)


def _mlp() -> ArchitectureGraph:
    return ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp"),), edges=())


def _autoencoder() -> ArchitectureGraph:
    return _chain(
        (
            NodeGene(id="encoder", block_id="encoder"),
            NodeGene(id="decoder", block_id="decoder"),
        )
    )


def _cnn1d() -> ArchitectureGraph:
    return _chain(
        (
            NodeGene(id="conv", block_id="conv1d"),
            NodeGene(id="pool", block_id="global_avg_pool_1d"),
            NodeGene(id="head", block_id="mlp"),
        )
    )


def _sequence(block_id: str) -> ArchitectureGraph:
    return _chain(
        (
            NodeGene(id="body", block_id=block_id),
            NodeGene(id="pool", block_id="sequence_pool"),
            NodeGene(id="head", block_id="mlp"),
        )
    )


def _gnn(block_id: str) -> ArchitectureGraph:
    return _chain(
        (
            NodeGene(id="gnn", block_id=block_id),
            NodeGene(id="pool", block_id="graph_global_pool"),
            NodeGene(id="to_vec", block_id="graph_embedding_to_vector"),
            NodeGene(id="head", block_id="mlp"),
        )
    )


_SKILL_GRAPHS: dict[str, Callable[[], ArchitectureGraph]] = {
    "neural.mlp.regressor": _mlp,
    "neural.mlp.classifier": _mlp,
    "neural.autoencoder.basic": _autoencoder,
    "neural.autoencoder.denoising": _autoencoder,
    "neural.cnn1d": _cnn1d,
    "neural.lstm": lambda: _sequence("lstm"),
    "neural.gru": lambda: _sequence("gru"),
    "neural.tcn": lambda: _sequence("tcn"),
    "neural.transformer.encoder": lambda: _sequence("transformer_encoder"),
    "neural.transformer.sequence_regressor": lambda: _sequence("transformer_encoder"),
    "neural.transformer.sequence_classifier": lambda: _sequence("transformer_encoder"),
    "neural.gcn": lambda: _gnn("gcn"),
    "neural.graphsage": lambda: _gnn("graphsage"),
    "neural.gat": lambda: _gnn("gat"),
}


def mapped_skill_ids() -> tuple[str, ...]:
    return tuple(sorted(_SKILL_GRAPHS))
