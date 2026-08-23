"""Closed mutation/crossover on ArchitectureGraph (ADR 0047 follow-on).

No free Python fitness. Operators are a closed catalog. Offspring that fail
``validate_graph`` are rejected. TITAN is not involved.
"""

from __future__ import annotations

import random
from typing import Literal

from oec.neural.architecture.default_catalog import default_registry
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.graph import ArchitectureGraph, EdgeGene, NodeGene
from oec.neural.architecture.registry import BlockRegistry

MutationOperator = Literal["widen", "deepen", "swap_activation"]
CrossoverOperator = Literal["one_point_chain"]

_WIDTH_LADDER = (8, 16, 32, 64)
_ACTIVATIONS = ("relu", "gelu", "silu", "tanh")
_WIDTH_KEYS = ("hidden_dim", "out_features", "out_channels", "d_model")


def mutate_graph(
    graph: ArchitectureGraph,
    *,
    operator: MutationOperator,
    seed: int = 0,
    registry: BlockRegistry | None = None,
) -> ArchitectureGraph:
    registry = registry or default_registry
    report = graph.validate_graph(registry)
    if not report.valid:
        raise ArchitectureValidationError(
            "cannot mutate an invalid architecture graph: " + "; ".join(report.errors)
        )
    rng = random.Random(int(seed))
    if operator == "widen":
        child = _widen(graph, rng)
    elif operator == "deepen":
        child = _deepen(graph)
    elif operator == "swap_activation":
        child = _swap_activation(graph, rng)
    else:
        raise ArchitectureValidationError(
            f"unknown mutation operator {operator!r}",
            details={"known": ["widen", "deepen", "swap_activation"]},
        )
    child_report = child.validate_graph(registry)
    if not child_report.valid:
        raise ArchitectureValidationError(
            "mutation produced an invalid graph: " + "; ".join(child_report.errors)
        )
    return child


def crossover_graphs(
    first: ArchitectureGraph,
    second: ArchitectureGraph,
    *,
    operator: CrossoverOperator = "one_point_chain",
    seed: int = 0,
    registry: BlockRegistry | None = None,
) -> ArchitectureGraph:
    registry = registry or default_registry
    for graph, label in ((first, "first"), (second, "second")):
        report = graph.validate_graph(registry)
        if not report.valid:
            raise ArchitectureValidationError(
                f"cannot cross {label} parent: " + "; ".join(report.errors)
            )
    if operator != "one_point_chain":
        raise ArchitectureValidationError(
            f"unknown crossover operator {operator!r}",
            details={"known": ["one_point_chain"]},
        )
    rng = random.Random(int(seed))
    child = _one_point_chain(first, second, rng)
    child_report = child.validate_graph(registry)
    if not child_report.valid:
        raise ArchitectureValidationError(
            "crossover produced an invalid graph: " + "; ".join(child_report.errors)
        )
    return child


def _widen(graph: ArchitectureGraph, rng: random.Random) -> ArchitectureGraph:
    candidates = [
        node
        for node in graph.nodes
        if any(key in node.config and isinstance(node.config[key], int) for key in _WIDTH_KEYS)
    ]
    if not candidates:
        raise ArchitectureValidationError("widen requires an int width field on some node")
    target = rng.choice(candidates)
    bumped: str | None = None
    new_width: int | None = None
    nodes = []
    for node in graph.nodes:
        if node.id != target.id:
            nodes.append(node)
            continue
        cfg = dict(node.config)
        for key in _WIDTH_KEYS:
            if key not in cfg or type(cfg[key]) is not int:
                continue
            nxt = _next_width(int(cfg[key]))
            if nxt is not None:
                cfg[key] = nxt
                bumped = key
                new_width = nxt
                break
        if bumped is None or new_width is None:
            raise ArchitectureValidationError("widen could not bump any width on the selected node")
        nodes.append(NodeGene(id=node.id, block_id=node.block_id, config=cfg))
    if bumped == "out_features" and new_width is not None:
        nodes = _align_next_in_features(graph, target.id, new_width, tuple(nodes))
    return ArchitectureGraph(nodes=tuple(nodes), edges=graph.edges, version=graph.version)


def _align_next_in_features(
    graph: ArchitectureGraph,
    source_id: str,
    width: int,
    nodes: tuple[NodeGene, ...],
) -> list[NodeGene]:
    successors = {edge.target for edge in graph.edges if edge.source == source_id}
    aligned = []
    for node in nodes:
        if node.id in successors and "in_features" in node.config:
            cfg = dict(node.config)
            cfg["in_features"] = width
            aligned.append(NodeGene(id=node.id, block_id=node.block_id, config=cfg))
        else:
            aligned.append(node)
    return aligned


def _next_width(current: int) -> int | None:
    for value in _WIDTH_LADDER:
        if value > current:
            return value
    return None


def _deepen(graph: ArchitectureGraph) -> ArchitectureGraph:
    linear = [node for node in graph.nodes if node.block_id == "linear"]
    if len(linear) < 1:
        raise ArchitectureValidationError("deepen requires at least one linear node")
    anchor = linear[0]
    width = int(anchor.config.get("out_features") or anchor.config.get("in_features") or 8)
    new_id = f"{anchor.id}_deep"
    inserted = NodeGene(
        id=new_id,
        block_id="linear",
        config={
            "in_features": width,
            "out_features": width,
            "activation": str(anchor.config.get("activation", "relu")),
        },
    )
    nodes = []
    for node in graph.nodes:
        nodes.append(node)
        if node.id == anchor.id:
            nodes.append(inserted)
    outgoing = [edge.target for edge in graph.edges if edge.source == anchor.id]
    edges = []
    for edge in graph.edges:
        if edge.source == anchor.id:
            edges.append(
                EdgeGene(
                    source=new_id,
                    target=edge.target,
                    source_port=edge.source_port,
                    target_port=edge.target_port,
                )
            )
        else:
            edges.append(edge)
    edges.append(EdgeGene(source=anchor.id, target=new_id))
    if not outgoing and len(graph.nodes) == 1:
        return ArchitectureGraph(nodes=tuple(nodes), edges=tuple(edges), version=graph.version)
    return ArchitectureGraph(nodes=tuple(nodes), edges=tuple(edges), version=graph.version)


def _swap_activation(graph: ArchitectureGraph, rng: random.Random) -> ArchitectureGraph:
    candidates = [node for node in graph.nodes if "activation" in node.config]
    if not candidates:
        raise ArchitectureValidationError("swap_activation requires a node with activation")
    target = rng.choice(candidates)
    current = str(target.config.get("activation", "relu"))
    options = [name for name in _ACTIVATIONS if name != current]
    if not options:
        options = list(_ACTIVATIONS)
    nxt = rng.choice(options)
    nodes = []
    for node in graph.nodes:
        if node.id != target.id:
            nodes.append(node)
            continue
        cfg = dict(node.config)
        cfg["activation"] = nxt
        nodes.append(NodeGene(id=node.id, block_id=node.block_id, config=cfg))
    return ArchitectureGraph(nodes=tuple(nodes), edges=graph.edges, version=graph.version)


def _one_point_chain(
    first: ArchitectureGraph,
    second: ArchitectureGraph,
    rng: random.Random,
) -> ArchitectureGraph:
    if not _is_linear_chain(first) or not _is_linear_chain(second):
        raise ArchitectureValidationError("one_point_chain requires two linear-chain parents")
    limit = min(len(first.nodes), len(second.nodes))
    if limit < 2:
        raise ArchitectureValidationError(
            "one_point_chain requires parents with at least two nodes"
        )
    cut = rng.randint(1, limit - 1)
    left = list(first.nodes[:cut])
    right = list(second.nodes[cut:])
    nodes = []
    for i, node in enumerate([*left, *right]):
        nodes.append(NodeGene(id=f"n{i}", block_id=node.block_id, config=dict(node.config)))
    edges = tuple(
        EdgeGene(source=nodes[i].id, target=nodes[i + 1].id) for i in range(len(nodes) - 1)
    )
    return ArchitectureGraph(nodes=tuple(nodes), edges=edges, version=first.version)


def _is_linear_chain(graph: ArchitectureGraph) -> bool:
    if not graph.nodes:
        return False
    if len(graph.edges) != len(graph.nodes) - 1:
        return False
    ids = [node.id for node in graph.nodes]
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in ids}
    incoming: dict[str, list[str]] = {node_id: [] for node_id in ids}
    for edge in graph.edges:
        outgoing[edge.source].append(edge.target)
        incoming[edge.target].append(edge.source)
    return all(len(outgoing[i]) <= 1 and len(incoming[i]) <= 1 for i in ids)
