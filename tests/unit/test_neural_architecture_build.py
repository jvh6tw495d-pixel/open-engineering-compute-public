"""A7 torch builder for ArchitectureGraph (ADR 0047)."""

from __future__ import annotations

import pytest

from oec.kernel.neural.architecture_build import build_architecture
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.neural.architecture import ArchitectureGraph, EdgeGene, NodeGene, default_registry
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
    graph = ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp"),), edges=())
    with pytest.raises(ValueError, match="unsupported architecture backend"):
        build_architecture(graph, backend="jax")


def test_unknown_block_still_has_no_torch_builder() -> None:
    graph = ArchitectureGraph(nodes=(NodeGene(id="n", block_id="not_a_block"),), edges=())
    with pytest.raises(ArchitectureValidationError):
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
    # An arity-1 block (single "in" port) wired from two sources fails the
    # graph-level port-wiring check before A7's chain builder even runs.
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
    with pytest.raises(ArchitectureValidationError, match="ports wired more than once"):
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
    with pytest.raises(ArchitectureValidationError, match="ports wired more than once"):
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


@pytest.mark.neural
def test_two_width_mlp_chain_forward() -> None:
    pytest.importorskip("torch")
    import torch

    graph = graph_for_skill(
        "neural.mlp.classifier",
        {
            "x": [[0.0, 1.0, 2.0, 3.0]],
            "hidden_dims": [32, 16],
            "n_classes": 3,
        },
    )
    assert len(graph.nodes) > 1
    assert graph.validate_graph(default_registry).valid
    model = build_architecture(graph)
    out = model(torch.zeros(5, 4))
    assert tuple(out.shape) == (5, 3)


@pytest.mark.neural
def test_kan_forward() -> None:
    pytest.importorskip("torch")
    import torch

    for basis in ("bspline", "rbf"):
        graph = ArchitectureGraph(
            nodes=(
                NodeGene(
                    id="k",
                    block_id="kan",
                    config={"in_features": 4, "out_features": 3, "basis": basis, "grid_size": 5},
                ),
            ),
            edges=(),
        )
        model = build_architecture(graph)
        out = model(torch.zeros(2, 4))
        assert tuple(out.shape) == (2, 3)


@pytest.mark.neural
def test_gnn_forward_requires_edge_index() -> None:
    pytest.importorskip("torch")
    import torch

    graph = graph_for_skill(
        "neural.gcn",
        {"node_features": [[0.0, 0.0]] * 5, "n_classes": 1},
    )
    model = build_architecture(graph)
    features = torch.randn(5, 2)
    edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=torch.long)
    out = model({"features": features, "edge_index": edge_index})
    assert out.shape[-1] == 1
    with pytest.raises(ArchitectureValidationError, match="edge_index"):
        model(features)


@pytest.mark.neural
def test_fno_1d_forward_preserves_rank() -> None:
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="f",
                block_id="fno",
                config={"in_channels": 2, "out_channels": 3, "modes": 4},
            ),
        ),
        edges=(),
    )
    model = build_architecture(graph)
    out = model(torch.randn(2, 2, 16))
    assert tuple(out.shape) == (2, 3, 16)


@pytest.mark.neural
def test_fno_2d_forward_preserves_rank() -> None:
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="f",
                block_id="fno_2d",
                config={"in_channels": 2, "out_channels": 3, "modes": 4},
            ),
        ),
        edges=(),
    )
    model = build_architecture(graph)
    out = model(torch.randn(2, 2, 8, 8))
    assert tuple(out.shape) == (2, 3, 8, 8)


@pytest.mark.neural
@pytest.mark.parametrize(
    ("block_id", "config", "in_shape", "out_shape"),
    [
        ("geglu", {"in_features": 4, "hidden_dim": 8}, (2, 3, 4), (2, 3, 4)),
        ("highway", {"in_features": 6}, (2, 6), (2, 6)),
        ("residual_gated", {"in_features": 6}, (2, 6), (2, 6)),
        ("swiglu", {"in_features": 6, "hidden_dim": 12}, (2, 6), (2, 6)),
        ("residual_mlp", {"in_features": 6, "hidden_dim": 12}, (2, 6), (2, 6)),
        ("self_attention", {"d_model": 8, "nhead": 2}, (2, 3, 8), (2, 3, 8)),
        ("vector_to_sequence", {}, (2, 6), (2, 1, 6)),
        ("depthwise_conv2d", {"in_channels": 4, "kernel_size": 3}, (2, 4, 8, 8), (2, 4, 8, 8)),
        (
            "separable_conv2d",
            {"in_channels": 4, "out_channels": 6, "kernel_size": 3},
            (2, 4, 8, 8),
            (2, 6, 8, 8),
        ),
        (
            "dilated_conv1d",
            {"in_channels": 4, "out_channels": 6, "kernel_size": 3, "dilation": 2},
            (2, 4, 16),
            (2, 6, 16),
        ),
        (
            "grouped_conv2d",
            {"in_channels": 4, "out_channels": 8, "kernel_size": 3, "groups": 2},
            (2, 4, 8, 8),
            (2, 8, 8, 8),
        ),
        (
            "squeeze_excitation",
            {"in_channels": 4, "reduction": 2},
            (2, 4, 8, 8),
            (2, 4, 8, 8),
        ),
        (
            "tcn",
            {"input_size": 4, "hidden_dim": 8, "n_layers": 2, "kernel_size": 3},
            (2, 5, 4),
            (2, 5, 8),
        ),
    ],
)
def test_a6_extra_forward_shapes(
    block_id: str, config: dict[str, object], in_shape: tuple[int, ...], out_shape: tuple[int, ...]
) -> None:
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(nodes=(NodeGene(id="n", block_id=block_id, config=config),), edges=())
    model = build_architecture(graph)
    out = model(torch.zeros(*in_shape))
    assert tuple(out.shape) == out_shape


@pytest.mark.neural
def test_cross_attention_named_port_forward() -> None:
    """The named-port proof: transformer_encoder (query) x self_attention (context)
    both feed a cross_attention join; a unary wiring fails closed."""
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="query_src",
                block_id="transformer_encoder",
                config={"d_model": 8, "nhead": 2, "dim_feedforward": 16, "num_layers": 1},
            ),
            NodeGene(
                id="context_src", block_id="self_attention", config={"d_model": 8, "nhead": 2}
            ),
            NodeGene(id="cross", block_id="cross_attention", config={"d_model": 8, "nhead": 2}),
        ),
        edges=(
            EdgeGene(source="query_src", target="cross", target_port="query"),
            EdgeGene(source="context_src", target="cross", target_port="context"),
        ),
    )
    model = build_architecture(graph)
    out = model(torch.zeros(2, 3, 8))
    assert tuple(out.shape) == (2, 3, 8)


def test_cross_attention_unary_wiring_fails_closed() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="query_src", block_id="transformer_encoder"),
            NodeGene(id="cross", block_id="cross_attention"),
        ),
        edges=(EdgeGene(source="query_src", target="cross", target_port="query"),),
    )
    with pytest.raises(ArchitectureValidationError, match="context"):
        build_architecture(graph)


@pytest.mark.neural
def test_gnn_chain_gcn_then_graphsage_uses_edge_index_on_both() -> None:
    """MAJOR 5: a non-root graph block must still receive edge_index, not
    fall through to the unary invocation path."""
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="gcn1",
                block_id="gcn",
                config={"input_size": 2, "hidden_dim": 4, "n_layers": 1},
            ),
            NodeGene(
                id="sage1",
                block_id="graphsage",
                config={"input_size": 4, "hidden_dim": 3, "n_layers": 1},
            ),
        ),
        edges=(EdgeGene(source="gcn1", target="sage1"),),
    )
    model = build_architecture(graph)
    features = torch.randn(5, 2)
    edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=torch.long)
    out = model({"features": features, "edge_index": edge_index})
    assert tuple(out.shape) == (5, 3)


@pytest.mark.neural
def test_gnn_output_depends_on_edge_index() -> None:
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="g",
                block_id="gcn",
                config={"input_size": 2, "hidden_dim": 4, "n_layers": 1},
            ),
        ),
        edges=(),
    )
    model = build_architecture(graph)
    features = torch.randn(5, 2)
    edge_index_a = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=torch.long)
    edge_index_b = torch.tensor([[0, 0, 0, 0], [1, 2, 3, 4]], dtype=torch.long)
    out_a = model({"features": features, "edge_index": edge_index_a})
    out_b = model({"features": features, "edge_index": edge_index_b})
    assert not torch.allclose(out_a, out_b)


@pytest.mark.neural
def test_kan_is_not_a_linear_gelu_stand_in() -> None:
    pytest.importorskip("torch")
    import torch
    import torch.nn as nn

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="k",
                block_id="kan",
                config={"in_features": 4, "out_features": 3, "basis": "bspline", "grid_size": 5},
            ),
        ),
        edges=(),
    )
    model = build_architecture(graph)
    kan_module = model.k
    assert hasattr(kan_module, "weight")
    assert kan_module.weight.dim() == 3  # (in_features, n_basis, out_features)
    assert isinstance(kan_module.base, nn.Linear)

    x = torch.randn(2, 4)
    out = model(x)
    permuted = x[:, [1, 0, 3, 2]]
    out_permuted = model(permuted)
    assert not torch.allclose(out, out_permuted)

    baseline = nn.Sequential(nn.Linear(4, 3), nn.GELU())
    with torch.no_grad():
        baseline[0].weight.copy_(kan_module.base.weight)
        baseline[0].bias.copy_(kan_module.base.bias)
    assert not torch.allclose(out, baseline(x))


@pytest.mark.neural
def test_fno_1d_rejects_wrong_rank_input() -> None:
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="f", block_id="fno", config={"in_channels": 2, "out_channels": 3, "modes": 4}
            ),
        ),
        edges=(),
    )
    model = build_architecture(graph)
    with pytest.raises(ArchitectureValidationError, match="rank"):
        model(torch.randn(2, 16))


@pytest.mark.neural
def test_fno_2d_rejects_wrong_rank_input() -> None:
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="f",
                block_id="fno_2d",
                config={"in_channels": 2, "out_channels": 3, "modes": 4},
            ),
        ),
        edges=(),
    )
    model = build_architecture(graph)
    out = model(torch.randn(2, 2, 8, 8))
    assert out.dim() == 4
    with pytest.raises(ArchitectureValidationError, match="rank"):
        model(torch.randn(2, 2, 8))


@pytest.mark.neural
def test_neural_ode_euler_preserves_vector() -> None:
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="ode",
                block_id="neural_ode",
                config={"in_features": 4, "hidden_dim": 8, "steps": 3},
            ),
        ),
        edges=(),
    )
    out = build_architecture(graph)(torch.zeros(2, 4))
    assert tuple(out.shape) == (2, 4)


@pytest.mark.neural
def test_pinn_motif_is_mlp_shaped() -> None:
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="pinn",
                block_id="pinn_motif",
                config={"in_features": 3, "hidden_dim": 8, "out_features": 1, "n_layers": 2},
            ),
        ),
        edges=(),
    )
    out = build_architecture(graph)(torch.zeros(5, 3))
    assert tuple(out.shape) == (5, 1)


@pytest.mark.neural
def test_local_and_linear_attention_keep_sequence_rank() -> None:
    pytest.importorskip("torch")
    import torch

    local = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="a",
                block_id="local_attention",
                config={"d_model": 8, "nhead": 2, "window": 4},
            ),
        ),
        edges=(),
    )
    linear = ArchitectureGraph(
        nodes=(NodeGene(id="a", block_id="linear_attention", config={"d_model": 8, "nhead": 2}),),
        edges=(),
    )
    for graph in (local, linear):
        out = build_architecture(graph)(torch.zeros(2, 7, 8))
        assert tuple(out.shape) == (2, 7, 8)
    one = build_architecture(
        ArchitectureGraph(
            nodes=(
                NodeGene(id="a", block_id="linear_attention", config={"d_model": 8, "nhead": 1}),
            ),
            edges=(),
        )
    )
    two = build_architecture(linear)

    def _nhead(module: object) -> int:
        for child in module.modules():  # type: ignore[union-attr]
            nhead = getattr(child, "nhead", None)
            if type(nhead) is int:
                return nhead
        raise AssertionError("linear_attention module did not expose nhead")

    assert _nhead(one) == 1
    assert _nhead(two) == 2


@pytest.mark.neural
def test_deeponet_named_ports() -> None:
    pytest.importorskip("torch")
    import torch

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="b",
                block_id="linear",
                config={"in_features": 4, "out_features": 4, "activation": "none"},
            ),
            NodeGene(
                id="t",
                block_id="linear",
                config={"in_features": 4, "out_features": 4, "activation": "none"},
            ),
            NodeGene(
                id="op",
                block_id="deeponet",
                config={"branch_dim": 4, "trunk_dim": 4, "hidden_dim": 8, "p": 4},
            ),
        ),
        edges=(
            EdgeGene(source="b", target="op", target_port="branch"),
            EdgeGene(source="t", target="op", target_port="trunk"),
        ),
    )
    out = build_architecture(graph)(torch.zeros(3, 4))
    assert tuple(out.shape) == (3, 1)
