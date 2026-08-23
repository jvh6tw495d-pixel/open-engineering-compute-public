"""Closed mutation/crossover on ArchitectureGraph (ADR 0047 follow-on).

No free Python fitness. Operators are a closed catalog. Offspring that fail
``validate_for_backend`` are rejected. TITAN is not involved.

Crossover policy: ``one_point_chain`` only crosses two linear chains of the
**same** ``NeuralFamily``, same graph ``version``, against the same sealed
catalog. The cut is in topological order. The stitch copies the left
output dim onto the right input dim when both sides declare a signature.
"""

from __future__ import annotations

import random
from typing import Literal

from oec.neural.architecture.compatibility import check_connection
from oec.neural.architecture.default_catalog import default_registry
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.governance import validate_for_backend
from oec.neural.architecture.graph import ArchitectureGraph, EdgeGene, NodeGene
from oec.neural.architecture.registry import BlockRegistry
from oec.neural.architecture.shapes import (
    OUTPUT_DIM_KEY,
    input_dim_key,
    output_dim_key,
    propagate_output_width,
)
from oec.neural.architecture.types import NeuralFamily

MutationOperator = Literal["widen", "deepen", "swap_activation"]
CrossoverOperator = Literal["one_point_chain"]

_WIDTH_LADDER = (8, 16, 32, 64)
_ACTIVATIONS = ("relu", "gelu", "silu", "tanh")
_WIDTH_KEYS = ("hidden_dim", "out_features", "out_channels", "d_model")

# Explicit closed table: a family only crosses itself.
CROSSABLE_FAMILIES: dict[NeuralFamily, frozenset[NeuralFamily]] = {
    family: frozenset({family}) for family in NeuralFamily
}


def mutate_graph(
    graph: ArchitectureGraph,
    *,
    operator: MutationOperator,
    seed: int = 0,
    registry: BlockRegistry | None = None,
) -> ArchitectureGraph:
    registry = registry or default_registry
    _require_backend_ready(graph, registry, "cannot mutate")
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
    _require_backend_ready(child, registry, "mutation produced")
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
        _require_backend_ready(graph, registry, f"cannot cross {label} parent")
    if operator != "one_point_chain":
        raise ArchitectureValidationError(
            f"unknown crossover operator {operator!r}",
            details={"known": ["one_point_chain"]},
        )
    rng = random.Random(int(seed))
    child = _one_point_chain(first, second, rng, registry)
    _require_backend_ready(child, registry, "crossover produced")
    return child


def _require_backend_ready(graph: ArchitectureGraph, registry: BlockRegistry, prefix: str) -> None:
    report = validate_for_backend(graph, "torch", registry)
    if not report.valid:
        raise ArchitectureValidationError(
            f"{prefix} an invalid architecture graph: " + "; ".join(report.errors)
        )


def _widen(graph: ArchitectureGraph, rng: random.Random) -> ArchitectureGraph:
    candidates = [
        node
        for node in graph.nodes
        if any(
            key in node.config
            and type(node.config[key]) is int
            and _next_width(int(node.config[key])) is not None
            for key in _WIDTH_KEYS
        )
    ]
    if not candidates:
        raise ArchitectureValidationError("widen requires an int width field on some node")
    target = rng.choice(candidates)
    bumped: str | None = None
    new_width: int | None = None
    nodes: list[NodeGene] = []
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
    if new_width is None:
        raise ArchitectureValidationError("widen could not bump any width on the selected node")
    out_key = output_dim_key(target.block_id)
    if bumped == out_key or bumped == "d_model":
        nodes = propagate_output_width(tuple(nodes), graph.edges, target.id, new_width)
    return ArchitectureGraph(nodes=tuple(nodes), edges=graph.edges, version=graph.version)


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
    child = ArchitectureGraph(nodes=tuple(nodes), edges=tuple(edges), version=graph.version)
    aligned = propagate_output_width(child.nodes, child.edges, new_id, width)
    return ArchitectureGraph(nodes=tuple(aligned), edges=child.edges, version=child.version)


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


def _family_of(graph: ArchitectureGraph, registry: BlockRegistry) -> NeuralFamily:
    families = {registry.get(node.block_id).family for node in graph.nodes}
    if len(families) != 1:
        raise ArchitectureValidationError(
            "one_point_chain requires a single NeuralFamily per parent; "
            f"got {sorted(family.value for family in families)}"
        )
    return next(iter(families))


def _ordered_nodes(graph: ArchitectureGraph) -> list[NodeGene]:
    node_map = {node.id: node for node in graph.nodes}
    return [node_map[node_id] for node_id in graph.topological_order()]


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


def _one_point_chain(
    first: ArchitectureGraph,
    second: ArchitectureGraph,
    rng: random.Random,
    registry: BlockRegistry,
) -> ArchitectureGraph:
    if first.version != second.version:
        raise ArchitectureValidationError("one_point_chain requires parents with the same version")
    if not _is_linear_chain(first) or not _is_linear_chain(second):
        raise ArchitectureValidationError("one_point_chain requires two linear-chain parents")
    left_family = _family_of(first, registry)
    right_family = _family_of(second, registry)
    allowed = CROSSABLE_FAMILIES.get(left_family, frozenset())
    if right_family not in allowed:
        raise ArchitectureValidationError(
            f"one_point_chain cannot cross {left_family.value} with {right_family.value}",
            details={
                "left": left_family.value,
                "right": right_family.value,
                "crossable": sorted(family.value for family in allowed),
            },
        )
    first_nodes = _ordered_nodes(first)
    second_nodes = _ordered_nodes(second)
    limit = min(len(first_nodes), len(second_nodes))
    if limit < 2:
        raise ArchitectureValidationError(
            "one_point_chain requires parents with at least two nodes"
        )
    cut = rng.randint(1, limit - 1)
    left = first_nodes[:cut]
    right = second_nodes[cut:]
    left_spec = registry.get(left[-1].block_id)
    right_spec = registry.get(right[0].block_id)
    compatibility = check_connection(left_spec, right_spec, registry)
    if not compatibility.compatible:
        raise ArchitectureValidationError(
            "one_point_chain cut is not kind-compatible: " + compatibility.reason
        )
    stitched_right = list(right)
    out_key = OUTPUT_DIM_KEY.get(left[-1].block_id)
    in_key = input_dim_key(right[0].block_id, "in")
    if out_key is not None and in_key is not None:
        width = left[-1].config.get(out_key)
        if type(width) is int:
            cfg = dict(right[0].config)
            cfg[in_key] = width
            stitched_right[0] = NodeGene(id=right[0].id, block_id=right[0].block_id, config=cfg)
    nodes = []
    for i, node in enumerate([*left, *stitched_right]):
        nodes.append(NodeGene(id=f"n{i}", block_id=node.block_id, config=dict(node.config)))
    edges = tuple(
        EdgeGene(source=nodes[i].id, target=nodes[i + 1].id) for i in range(len(nodes) - 1)
    )
    return ArchitectureGraph(nodes=tuple(nodes), edges=edges, version=first.version)
