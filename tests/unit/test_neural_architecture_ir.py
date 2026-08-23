"""Neural Architecture IR A0–A4 (ADR 0047). Core-safe, no torch."""

from __future__ import annotations

import subprocess
import sys

import pytest
from pydantic import ValidationError

from oec.neural.architecture import (
    ArchitectureGraph,
    BlockCategory,
    BlockSpec,
    DuplicateBlockError,
    EdgeGene,
    NeuralFamily,
    NodeGene,
    RegistrySealedError,
    TensorKind,
    UnknownBlockError,
    UnknownFamilyError,
    check_connection,
    default_registry,
    make_default_registry,
)


def test_import_does_not_require_torch() -> None:
    import oec.neural.architecture as arch

    assert "torch" not in getattr(arch, "__dict__", {})
    assert arch.default_registry.version == "0.2.5"


def test_architecture_import_does_not_load_torch_in_clean_process() -> None:
    code = (
        "import sys; "
        "assert 'torch' not in sys.modules; "
        "import oec.neural.architecture as arch; "
        "assert 'torch' not in sys.modules; "
        "assert 'torch' not in arch.__dict__"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_default_registry_has_expected_families() -> None:
    assert default_registry.by_family(NeuralFamily.FEEDFORWARD)
    assert default_registry.by_family(NeuralFamily.GRAPH)
    assert default_registry.by_family(NeuralFamily.KAN)


def test_vector_to_vector_candidates_include_mlp_and_kan() -> None:
    ids = {
        spec.id
        for spec in default_registry.compatible_blocks(
            input_kind=TensorKind.VECTOR,
            output_kind=TensorKind.VECTOR,
        )
    }
    assert "mlp" in ids
    assert "kan" in ids


def test_duplicate_registration_fails() -> None:
    registry = type(default_registry)(version="test")
    spec = default_registry.get("mlp")
    registry.register(spec)
    with pytest.raises(DuplicateBlockError):
        registry.register(spec)


def test_unknown_block_fails_closed() -> None:
    with pytest.raises(UnknownBlockError) as exc:
        default_registry.get("not_a_block")
    assert exc.value.code == "unknown_architecture_block"


def test_unknown_family_string_fails_closed() -> None:
    with pytest.raises(UnknownFamilyError) as exc:
        default_registry.by_family("unknown")
    assert exc.value.code == "unknown_architecture_family"
    assert exc.value.details["family"] == "unknown"


def test_unknown_family_wrong_type_fails_closed() -> None:
    with pytest.raises(UnknownFamilyError) as exc:
        default_registry.by_family(123)
    assert exc.value.code == "unknown_architecture_family"
    assert exc.value.details["type"] == "int"


def test_known_family_without_blocks_is_empty() -> None:
    assert default_registry.by_family(NeuralFamily.SPIKING)
    assert default_registry.by_family("feedforward")


def test_missing_required_parameter_fails_closed() -> None:
    graph = ArchitectureGraph(nodes=(NodeGene(id="lin", block_id="linear"),), edges=())
    report = graph.validate_graph(default_registry)
    assert not report.valid
    assert any("out_features" in error for error in report.errors)


def test_unknown_config_key_fails_closed() -> None:
    graph = ArchitectureGraph(
        nodes=(NodeGene(id="mlp", block_id="mlp", config={"typo_dim": 4}),),
        edges=(),
    )
    report = graph.validate_graph(default_registry)
    assert not report.valid
    assert any("unknown config keys" in error for error in report.errors)


def test_config_type_and_range_fail_closed() -> None:
    wrong_type = ArchitectureGraph(
        nodes=(NodeGene(id="mlp", block_id="mlp", config={"hidden_dim": "wide"}),),
        edges=(),
    )
    too_small = ArchitectureGraph(
        nodes=(NodeGene(id="mlp", block_id="mlp", config={"hidden_dim": 1}),),
        edges=(),
    )
    bad_choice = ArchitectureGraph(
        nodes=(NodeGene(id="mlp", block_id="mlp", config={"activation": "not_an_act"}),),
        edges=(),
    )
    for graph, needle in (
        (wrong_type, "must be int"),
        (too_small, "below minimum"),
        (bad_choice, "not in choices"),
    ):
        report = graph.validate_graph(default_registry)
        assert not report.valid
        assert any(needle in error for error in report.errors)


def test_attention_head_split_mismatch_fails_closed_before_torch() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="t",
                block_id="transformer_encoder",
                config={"d_model": 10, "nhead": 3, "dim_feedforward": 16, "num_layers": 1},
            ),
        ),
        edges=(),
    )
    report = graph.validate_graph(default_registry)
    assert not report.valid
    assert any("nhead" in error for error in report.errors)


def test_attention_head_exceeding_d_model_fails_closed() -> None:
    graph = ArchitectureGraph(
        nodes=(NodeGene(id="s", block_id="self_attention", config={"d_model": 4, "nhead": 8}),),
        edges=(),
    )
    report = graph.validate_graph(default_registry)
    assert not report.valid
    assert any("nhead" in error for error in report.errors)


def test_snapshot_is_sorted_and_serializable() -> None:
    snap = default_registry.snapshot()
    ids = [row["id"] for row in snap.blocks]
    assert ids == sorted(ids)
    assert snap.version == "0.2.5"


def test_conv2d_to_kan_requires_adapter() -> None:
    result = check_connection(
        default_registry.get("conv2d"),
        default_registry.get("kan"),
        default_registry,
    )
    assert not result.compatible
    assert "global_avg_pool_2d" in result.suggested_adapters
    assert "flatten" in result.suggested_adapters


def test_transformer_to_sequence_pool_is_valid() -> None:
    result = check_connection(
        default_registry.get("transformer_encoder"),
        default_registry.get("sequence_pool"),
        default_registry,
    )
    assert result.compatible


def test_graph_pool_chain() -> None:
    first = check_connection(
        default_registry.get("gcn"),
        default_registry.get("graph_global_pool"),
        default_registry,
    )
    second = check_connection(
        default_registry.get("graph_global_pool"),
        default_registry.get("graph_embedding_to_vector"),
        default_registry,
    )
    third = check_connection(
        default_registry.get("graph_embedding_to_vector"),
        default_registry.get("mlp"),
        default_registry,
    )
    assert first.compatible
    assert second.compatible
    assert third.compatible


def test_valid_conv_to_kan_graph_with_adapter() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="conv", block_id="conv2d"),
            NodeGene(id="pool", block_id="global_avg_pool_2d"),
            NodeGene(id="kan", block_id="kan"),
        ),
        edges=(
            EdgeGene(source="conv", target="pool"),
            EdgeGene(source="pool", target="kan"),
        ),
    )
    report = graph.validate_graph(default_registry)
    assert report.valid, report.errors
    assert any("experimental block: kan" in warning for warning in report.warnings)


def test_invalid_direct_conv_to_kan_graph() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="conv", block_id="conv2d"),
            NodeGene(id="kan", block_id="kan"),
        ),
        edges=(EdgeGene(source="conv", target="kan"),),
    )
    report = graph.validate_graph(default_registry)
    assert not report.valid
    assert any("global_avg_pool_2d" in error for error in report.errors)


def test_cycle_fails() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="mlp"),
            NodeGene(id="b", block_id="mlp"),
        ),
        edges=(
            EdgeGene(source="a", target="b"),
            EdgeGene(source="b", target="a"),
        ),
    )
    report = graph.validate_graph(default_registry)
    assert not report.valid
    assert "architecture graph is not a valid DAG" in report.errors


def test_fingerprint_is_order_stable() -> None:
    first = ArchitectureGraph(
        nodes=(NodeGene(id="x", block_id="mlp"), NodeGene(id="y", block_id="kan")),
        edges=(EdgeGene(source="x", target="y"),),
    )
    second = ArchitectureGraph(
        nodes=(NodeGene(id="y", block_id="kan"), NodeGene(id="x", block_id="mlp")),
        edges=(EdgeGene(source="x", target="y"),),
    )
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64


def test_fingerprint_normalizes_defaults() -> None:
    empty = ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp"),), edges=())
    explicit = ArchitectureGraph(
        nodes=(
            NodeGene(
                id="mlp",
                block_id="mlp",
                config={
                    "in_features": 8,
                    "hidden_dim": 128,
                    "activation": "gelu",
                },
            ),
        ),
        edges=(),
    )
    assert empty.fingerprint() == explicit.fingerprint()


def test_fingerprint_includes_catalog_hash() -> None:
    graph = ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp"),), edges=())
    payload = graph.canonical_dict()
    assert payload["registry_version"] == default_registry.version
    assert payload["catalog_hash"] == default_registry.catalog_hash()
    cloned = make_default_registry()
    cloned.version = "9.9.9"
    assert graph.fingerprint(cloned) != graph.fingerprint()


def test_non_finite_config_fails_closed() -> None:
    with pytest.raises(ValidationError, match="non-finite"):
        NodeGene(id="mlp", block_id="mlp", config={"hidden_dim": float("nan")})


def test_config_is_immutable() -> None:
    node = NodeGene(id="mlp", block_id="mlp", config={"hidden_dim": 16})
    with pytest.raises(TypeError):
        node.config["hidden_dim"] = 32  # type: ignore[index]


def test_default_registry_is_sealed() -> None:
    spec = default_registry.get("mlp")
    with pytest.raises(RegistrySealedError) as exc:
        default_registry.register(spec)
    assert exc.value.code == "architecture_registry_sealed"
    cloned = default_registry.clone()
    assert not cloned.sealed
    with pytest.raises(DuplicateBlockError):
        cloned.register(spec)


def test_unknown_source_port_fails_closed() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="mlp"),
            NodeGene(id="b", block_id="mlp"),
        ),
        edges=(EdgeGene(source="a", target="b", source_port="inexistente"),),
    )
    report = graph.validate_graph(default_registry)
    assert not report.valid
    assert any("source_port" in error for error in report.errors)


def test_output_ports_locked_to_out() -> None:
    with pytest.raises(ValidationError, match="output_ports"):
        BlockSpec(
            id="two_outs",
            display_name="Two Outs",
            family=NeuralFamily.FEEDFORWARD,
            category=BlockCategory.BLOCK,
            input_kinds=frozenset({TensorKind.VECTOR}),
            output_kind=TensorKind.VECTOR,
            output_ports=("left", "right"),
        )


def test_default_source_port_is_valid() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="mlp"),
            NodeGene(id="b", block_id="mlp"),
        ),
        edges=(EdgeGene(source="a", target="b"),),
    )
    report = graph.validate_graph(default_registry)
    assert report.valid, report.errors


def test_snapshot_includes_sorted_output_ports() -> None:
    snap = default_registry.snapshot()
    row = next(r for r in snap.blocks if r["id"] == "linear")
    assert row["output_ports"] == ["out"]


def test_orphan_nodes_fail_validation() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="mlp"),
            NodeGene(id="b", block_id="mlp"),
        ),
        edges=(),
    )
    report = graph.validate_graph(default_registry)
    assert not report.valid
    assert any("orphan node" in error for error in report.errors)
