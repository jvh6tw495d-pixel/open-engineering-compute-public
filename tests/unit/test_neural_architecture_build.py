"""A7 torch builder for ArchitectureGraph (ADR 0047)."""

from __future__ import annotations

import pytest

from oec.kernel.neural.architecture_build import build_architecture
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.neural.architecture import ArchitectureGraph, EdgeGene, NodeGene
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.skill_map import graph_for_skill

_NO_TORCH_BUILDER = (
    "kan",
    "gcn",
    "graphsage",
    "gat",
    "swiglu",
    "residual_mlp",
    "self_attention",
    "tcn",
    "vector_to_sequence",
    "geglu",
    "residual_gated",
    "highway",
    "depthwise_conv2d",
    "separable_conv2d",
    "dilated_conv1d",
    "grouped_conv2d",
    "squeeze_excitation",
    "cross_attention",
    "local_attention",
    "linear_attention",
    "neural_ode",
    "fno",
    "fno_2d",
    "deeponet",
    "pinn_motif",
)


def test_fail_closed_without_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.kernel.neural.architecture_build as build_mod

    def boom() -> None:
        raise TorchNotAvailableError("PyTorch is not installed")

    monkeypatch.setattr(build_mod, "_require_torch", boom)
    graph = ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp"),), edges=())
    with pytest.raises(TorchNotAvailableError):
        build_mod.build_architecture(graph)


def test_unknown_backend_fails() -> None:
    graph = ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp"),), edges=())
    with pytest.raises(ValueError, match="unsupported architecture backend"):
        build_architecture(graph, backend="jax")


def test_kan_fails_closed_even_with_torch() -> None:
    graph = ArchitectureGraph(nodes=(NodeGene(id="k", block_id="kan"),), edges=())
    with pytest.raises(ArchitectureValidationError, match="no torch builder"):
        build_architecture(graph)


@pytest.mark.parametrize("block_id", _NO_TORCH_BUILDER)
def test_unsupported_blocks_fail_closed_without_torch(block_id: str) -> None:
    graph = ArchitectureGraph(nodes=(NodeGene(id="n", block_id=block_id),), edges=())
    with pytest.raises(ArchitectureValidationError, match="no torch builder"):
        build_architecture(graph)


def test_empty_graph_fails_closed() -> None:
    with pytest.raises(ArchitectureValidationError, match="empty architecture graph"):
        build_architecture(ArchitectureGraph(nodes=(), edges=()))


def test_fork_fails_closed() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="mlp"),
            NodeGene(id="b", block_id="mlp"),
            NodeGene(id="c", block_id="mlp"),
        ),
        edges=(
            EdgeGene(source="a", target="b"),
            EdgeGene(source="a", target="c"),
        ),
    )
    with pytest.raises(ArchitectureValidationError, match="forked graphs"):
        build_architecture(graph)


def test_join_fails_closed() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="mlp"),
            NodeGene(id="b", block_id="mlp"),
            NodeGene(id="c", block_id="mlp"),
        ),
        edges=(
            EdgeGene(source="a", target="c"),
            EdgeGene(source="b", target="c"),
        ),
    )
    with pytest.raises(ArchitectureValidationError, match="branched graphs"):
        build_architecture(graph)


def test_skip_connection_fails_closed() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="mlp"),
            NodeGene(id="b", block_id="mlp"),
            NodeGene(id="c", block_id="mlp"),
        ),
        edges=(
            EdgeGene(source="a", target="b"),
            EdgeGene(source="b", target="c"),
            EdgeGene(source="a", target="c"),
        ),
    )
    with pytest.raises(ArchitectureValidationError, match="branched graphs"):
        build_architecture(graph)


def test_disconnected_nodes_fail_closed() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="mlp"),
            NodeGene(id="b", block_id="mlp"),
        ),
        edges=(),
    )
    with pytest.raises(ArchitectureValidationError, match="orphan"):
        build_architecture(graph)


@pytest.mark.neural
def test_mlp_forward() -> None:
    pytest.importorskip("torch")
    import torch

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

    graph = graph_for_skill(
        "neural.cnn1d",
        {
            "x": [[[0.0] * 16], [[0.0] * 16]],
            "hidden": 8,
            "kernel_size": 3,
            "n_classes": 1,
        },
    )
    model = build_architecture(graph)
    out = model(torch.zeros(2, 1, 16))
    assert tuple(out.shape) == (2, 1)
