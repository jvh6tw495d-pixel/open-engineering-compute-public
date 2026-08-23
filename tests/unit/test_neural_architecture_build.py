"""A7 torch builder for ArchitectureGraph (ADR 0047)."""

from __future__ import annotations

import pytest

from oec.kernel.neural.errors import TorchNotAvailableError
from oec.neural.architecture import ArchitectureGraph, NodeGene
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.skill_map import graph_for_skill


def test_fail_closed_without_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.kernel.neural.architecture_build as build_mod

    def boom() -> None:
        raise TorchNotAvailableError("PyTorch is not installed")

    monkeypatch.setattr(build_mod, "_require_torch", boom)
    graph = ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp"),), edges=())
    with pytest.raises(TorchNotAvailableError):
        build_mod.build_architecture(graph)


def test_unknown_backend_fails() -> None:
    from oec.kernel.neural.architecture_build import build_architecture

    graph = ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp"),), edges=())
    with pytest.raises(ValueError, match="unsupported architecture backend"):
        build_architecture(graph, backend="jax")


def test_kan_fails_closed_even_with_torch() -> None:
    pytest.importorskip("torch")
    from oec.kernel.neural.architecture_build import build_architecture

    graph = ArchitectureGraph(nodes=(NodeGene(id="k", block_id="kan"),), edges=())
    with pytest.raises(ArchitectureValidationError, match="no torch builder"):
        build_architecture(graph)


@pytest.mark.neural
def test_mlp_forward() -> None:
    pytest.importorskip("torch")
    import torch

    from oec.kernel.neural.architecture_build import build_architecture

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="mlp",
                block_id="mlp",
                config={"in_features": 4, "hidden_dim": 8, "out_features": 2},
            ),
        ),
        edges=(),
    )
    model = build_architecture(graph)
    out = model(torch.zeros(3, 4))
    assert tuple(out.shape) == (3, 2)


@pytest.mark.neural
def test_cnn1d_mapped_skill_forward() -> None:
    pytest.importorskip("torch")
    import torch

    from oec.kernel.neural.architecture_build import build_architecture

    graph = graph_for_skill("neural.cnn1d")
    nodes = []
    for node in graph.nodes:
        cfg = dict(node.config)
        if node.block_id == "conv1d":
            cfg.update({"in_channels": 1, "out_channels": 4, "kernel_size": 3})
        if node.block_id == "mlp":
            cfg.update({"in_features": 4, "hidden_dim": 8, "out_features": 1})
        nodes.append(NodeGene(id=node.id, block_id=node.block_id, config=cfg))
    built = ArchitectureGraph(nodes=tuple(nodes), edges=graph.edges)
    model = build_architecture(built)
    out = model(torch.zeros(2, 1, 16))
    assert tuple(out.shape) == (2, 1)
