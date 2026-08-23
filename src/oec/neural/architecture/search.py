"""Architecture-IR-governed search (ADR 0047 wave A8+). Core-safe orchestration.

This is *not* TITAN and it does not replace ``neural.search_architecture``
(ADR 0033's hybrid evolutionary training-facet search, which stays
independent). ``search_graphs`` enumerates a closed candidate family —
sequential MLP / CNN1d / LSTM graphs built from the governed catalog with
widths/depths drawn from a closed list of ints — validates every candidate,
and ranks them by a closed, built-in objective: a static parameter-count
estimate. There is no caller-supplied fitness callback of any kind — the
search never executes arbitrary Python to score a candidate.

No mutation/crossover operators live here — this is enumeration + ranking
over statically declared candidates, not population evolution.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from oec.neural.architecture.default_catalog import default_registry
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.governance import ArchitectureManifest, manifest_for_graph
from oec.neural.architecture.graph import ArchitectureGraph, EdgeGene, NodeGene
from oec.neural.architecture.registry import BlockRegistry

SearchFamily = Literal["mlp", "cnn1d", "lstm"]
SearchObjective = Literal["param_count"]


def _chain(nodes: tuple[NodeGene, ...]) -> ArchitectureGraph:
    edges = tuple(
        EdgeGene(source=nodes[i].id, target=nodes[i + 1].id) for i in range(len(nodes) - 1)
    )
    return ArchitectureGraph(nodes=nodes, edges=edges)


def _mlp_candidate(
    in_features: int, out_features: int, width: int, depth: int
) -> ArchitectureGraph:
    sizes = [in_features, *([width] * depth), out_features]
    nodes = []
    for i in range(len(sizes) - 1):
        activation = "relu" if i < len(sizes) - 2 else "none"
        nodes.append(
            NodeGene(
                id=f"linear_{i}",
                block_id="linear",
                config={
                    "in_features": sizes[i],
                    "out_features": sizes[i + 1],
                    "activation": activation,
                },
            )
        )
    return _chain(tuple(nodes))


def _cnn1d_candidate(
    in_features: int, out_features: int, width: int, depth: int
) -> ArchitectureGraph:
    nodes = []
    channels = in_features
    for i in range(depth):
        nodes.append(
            NodeGene(
                id=f"conv_{i}",
                block_id="conv1d",
                config={"in_channels": channels, "out_channels": width, "kernel_size": 3},
            )
        )
        channels = width
    nodes.append(NodeGene(id="pool", block_id="global_avg_pool_1d"))
    nodes.append(
        NodeGene(
            id="head",
            block_id="mlp",
            config={"in_features": width, "hidden_dim": width, "out_features": out_features},
        )
    )
    return _chain(tuple(nodes))


def _lstm_candidate(
    in_features: int, out_features: int, width: int, depth: int
) -> ArchitectureGraph:
    nodes = (
        NodeGene(
            id="body",
            block_id="lstm",
            config={"input_size": in_features, "hidden_dim": width, "n_layers": depth},
        ),
        NodeGene(id="pool", block_id="sequence_pool"),
        NodeGene(
            id="head",
            block_id="mlp",
            config={"in_features": width, "hidden_dim": width, "out_features": out_features},
        ),
    )
    return _chain(nodes)


_CANDIDATE_BUILDERS: dict[str, Callable[[int, int, int, int], ArchitectureGraph]] = {
    "mlp": _mlp_candidate,
    "cnn1d": _cnn1d_candidate,
    "lstm": _lstm_candidate,
}


def _estimate_block_params(block_id: str, config: dict[str, Any]) -> int:
    """Static structural estimate — deterministic formula, not a learned score."""
    if block_id == "linear":
        in_f = int(config["in_features"])
        out_f = int(config["out_features"])
        bias = out_f if config.get("bias", True) else 0
        return in_f * out_f + bias
    if block_id == "mlp":
        in_f = int(config["in_features"])
        hidden = int(config["hidden_dim"])
        out_f = int(config.get("out_features", hidden))
        return in_f * hidden + hidden + hidden * out_f + out_f
    if block_id == "conv1d":
        in_ch = int(config["in_channels"])
        out_ch = int(config["out_channels"])
        kernel = int(config["kernel_size"])
        return in_ch * out_ch * kernel + out_ch
    if block_id in {"lstm", "gru"}:
        in_sz = int(config["input_size"])
        hidden = int(config["hidden_dim"])
        n_layers = int(config["n_layers"])
        gates = 4 if block_id == "lstm" else 3
        # nn.LSTM / nn.GRU carry two bias vectors per layer (bias_ih, bias_hh).
        first_layer = gates * hidden * (in_sz + hidden + 2)
        other_layers = gates * hidden * (2 * hidden + 2) * max(n_layers - 1, 0)
        return first_layer + other_layers
    return 0


def _estimate_params(graph: ArchitectureGraph, registry: BlockRegistry) -> int:
    total = 0
    for node in graph.nodes:
        spec = registry.get(node.block_id)
        config = spec.validate_config(dict(node.config))
        total += _estimate_block_params(node.block_id, config)
    return total


def _validate_positive_int(label: str, value: int) -> None:
    if type(value) is not int or value < 1:
        raise ArchitectureValidationError(
            f"{label} must be an int >= 1; got {value!r}",
            details={"value": value},
        )


def _validate_positive_ints(label: str, values: Sequence[int]) -> None:
    if not values:
        raise ArchitectureValidationError(
            f"{label} must be a non-empty sequence of ints",
            details={"values": list(values)},
        )
    for value in values:
        if type(value) is not int or value < 1:
            raise ArchitectureValidationError(
                f"{label} must contain only ints >= 1; got {value!r}",
                details={"values": list(values), "value": value},
            )


class ArchitectureCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    graph: ArchitectureGraph
    score: float
    family: SearchFamily
    width: int
    depth: int


class ArchitectureSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    best: ArchitectureCandidate | None
    best_manifest: ArchitectureManifest | None
    objective: Literal["param_count_estimate"]
    candidates_evaluated: int
    candidates_rejected: tuple[str, ...] = ()


def search_graphs(
    family: SearchFamily,
    *,
    in_features: int = 8,
    out_features: int = 1,
    widths: Sequence[int] = (8, 16, 32),
    depths: Sequence[int] = (1, 2),
    registry: BlockRegistry | None = None,
    objective: SearchObjective = "param_count",
) -> ArchitectureSearchResult:
    """Enumerate a closed candidate family, validate each, and rank by the
    closed, built-in parameter-count objective. Never imports torch."""
    builder = _CANDIDATE_BUILDERS.get(family)
    if builder is None:
        raise ArchitectureValidationError(
            f"unknown search family {family!r}",
            details={"family": family, "known": sorted(_CANDIDATE_BUILDERS)},
        )
    if objective != "param_count":
        raise ArchitectureValidationError(
            f"unknown search objective {objective!r}",
            details={"objective": objective, "known": ["param_count"]},
        )
    _validate_positive_int("in_features", in_features)
    _validate_positive_int("out_features", out_features)
    _validate_positive_ints("widths", widths)
    _validate_positive_ints("depths", depths)
    registry = registry or default_registry

    candidates: list[ArchitectureCandidate] = []
    rejected: list[str] = []
    for width in widths:
        for depth in depths:
            graph = builder(in_features, out_features, width, depth)
            report = graph.validate_graph(registry)
            if not report.valid:
                rejected.append(f"{family} width={width} depth={depth}: {'; '.join(report.errors)}")
                continue
            score = float(_estimate_params(graph, registry))
            candidates.append(
                ArchitectureCandidate(
                    graph=graph, score=score, family=family, width=width, depth=depth
                )
            )

    if not candidates:
        return ArchitectureSearchResult(
            best=None,
            best_manifest=None,
            objective="param_count_estimate",
            candidates_evaluated=0,
            candidates_rejected=tuple(rejected),
        )
    best = min(candidates, key=lambda candidate: candidate.score)
    manifest = manifest_for_graph(best.graph, registry)
    return ArchitectureSearchResult(
        best=best,
        best_manifest=manifest,
        objective="param_count_estimate",
        candidates_evaluated=len(candidates),
        candidates_rejected=tuple(rejected),
    )
