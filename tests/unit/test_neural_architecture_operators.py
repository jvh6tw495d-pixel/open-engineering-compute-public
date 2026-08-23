"""Closed ArchitectureGraph mutation/crossover (no TITAN, no Python fitness)."""

from __future__ import annotations

import pytest

from oec.neural.architecture import (
    ArchitectureGraph,
    EdgeGene,
    NodeGene,
    default_registry,
    validate_for_backend,
)
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.operators import crossover_graphs, mutate_graph
from oec.neural.architecture.skill_map import graph_for_skill


def _linear_chain() -> ArchitectureGraph:
    return graph_for_skill(
        "neural.mlp.classifier",
        {"x": [[0.0, 1.0, 2.0, 3.0]], "hidden_dims": [8, 8], "n_classes": 2},
    )


def test_widen_bumps_closed_ladder() -> None:
    parent = _linear_chain()
    child = mutate_graph(parent, operator="widen", seed=0)
    assert child.fingerprint() != parent.fingerprint()
    assert child.validate_graph(default_registry).valid


def test_swap_activation_changes_enum() -> None:
    parent = _linear_chain()
    child = mutate_graph(parent, operator="swap_activation", seed=1)
    assert child.validate_graph(default_registry).valid
    parent_acts = [dict(n.config).get("activation") for n in parent.nodes]
    child_acts = [dict(n.config).get("activation") for n in child.nodes]
    assert parent_acts != child_acts


def test_deepen_inserts_linear() -> None:
    parent = _linear_chain()
    child = mutate_graph(parent, operator="deepen", seed=0)
    assert len(child.nodes) == len(parent.nodes) + 1
    assert child.validate_graph(default_registry).valid


def test_unknown_mutation_fails_closed() -> None:
    with pytest.raises(ArchitectureValidationError, match="unknown mutation"):
        mutate_graph(_linear_chain(), operator="titan")  # type: ignore[arg-type]


def test_one_point_crossover_validates() -> None:
    first = _linear_chain()
    second = graph_for_skill(
        "neural.mlp.classifier",
        {"x": [[0.0, 1.0, 2.0, 3.0]], "hidden_dims": [16, 8], "n_classes": 2},
    )
    child = crossover_graphs(first, second, operator="one_point_chain", seed=2)
    assert child.validate_graph(default_registry).valid
    assert len(child.nodes) >= 2


def test_crossover_rejects_invalid_parent() -> None:
    bad = ArchitectureGraph(nodes=(NodeGene(id="lin", block_id="linear"),), edges=())
    with pytest.raises(ArchitectureValidationError, match="first parent"):
        crossover_graphs(bad, _linear_chain())


def test_widen_aligns_conv_channels() -> None:
    parent = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="a",
                block_id="conv1d",
                config={"in_channels": 1, "out_channels": 8, "kernel_size": 3},
            ),
            NodeGene(
                id="b",
                block_id="conv1d",
                config={"in_channels": 8, "out_channels": 8, "kernel_size": 3},
            ),
        ),
        edges=(EdgeGene(source="a", target="b"),),
    )
    child = mutate_graph(parent, operator="widen", seed=0)
    node_map = {node.id: node for node in child.nodes}
    assert int(node_map["a"].config["out_channels"]) == int(node_map["b"].config["in_channels"])
    assert validate_for_backend(child, "torch", default_registry).valid
    assert child.fingerprint() != parent.fingerprint()


def test_crossover_uses_topological_order() -> None:
    first = ArchitectureGraph(
        nodes=(
            NodeGene(id="z", block_id="linear", config={"in_features": 4, "out_features": 8}),
            NodeGene(id="a", block_id="linear", config={"in_features": 8, "out_features": 2}),
        ),
        edges=(EdgeGene(source="z", target="a"),),
    )
    second = ArchitectureGraph(
        nodes=(
            NodeGene(id="tail", block_id="linear", config={"in_features": 16, "out_features": 2}),
            NodeGene(id="head", block_id="linear", config={"in_features": 4, "out_features": 16}),
        ),
        edges=(EdgeGene(source="head", target="tail"),),
    )
    child = crossover_graphs(first, second, operator="one_point_chain", seed=0)
    assert child.validate_graph(default_registry).valid
    assert child.nodes[0].config["in_features"] == 4


def test_crossover_rejects_family_mix() -> None:
    conv = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="a",
                block_id="conv1d",
                config={"in_channels": 1, "out_channels": 8, "kernel_size": 3},
            ),
            NodeGene(
                id="b",
                block_id="conv1d",
                config={"in_channels": 8, "out_channels": 8, "kernel_size": 3},
            ),
        ),
        edges=(EdgeGene(source="a", target="b"),),
    )
    with pytest.raises(ArchitectureValidationError, match="cannot cross"):
        crossover_graphs(_linear_chain(), conv)


def test_validate_for_backend_rejects_fork() -> None:
    forked = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="linear", config={"in_features": 4, "out_features": 8}),
            NodeGene(id="b", block_id="linear", config={"in_features": 8, "out_features": 2}),
            NodeGene(id="c", block_id="linear", config={"in_features": 8, "out_features": 2}),
        ),
        edges=(
            EdgeGene(source="a", target="b"),
            EdgeGene(source="a", target="c"),
        ),
    )
    assert forked.validate_graph(default_registry).valid
    report = validate_for_backend(forked, "torch", default_registry)
    assert not report.valid
    assert any("fork" in err for err in report.errors)
