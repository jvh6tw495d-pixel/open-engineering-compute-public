"""A8 governance (ADR 0047). Core-safe, no torch."""

from __future__ import annotations

import pytest

from oec.neural.architecture import (
    COMPATIBILITY_VERSION,
    ArchitectureGraph,
    ArchitectureProvenance,
    ArchitectureValidationError,
    EdgeGene,
    NodeGene,
    RegistrySealedError,
    audit_catalog,
    default_registry,
    make_default_registry,
    manifest_for_graph,
)
from oec.neural.architecture.specs import BlockParameterSpec, BlockSpec
from oec.neural.architecture.types import BlockCategory, NeuralFamily, TensorKind


def _mlp_graph() -> ArchitectureGraph:
    return ArchitectureGraph(nodes=(NodeGene(id="mlp", block_id="mlp"),), edges=())


def test_manifest_binds_fingerprint_to_catalog_state() -> None:
    graph = _mlp_graph()
    manifest = manifest_for_graph(graph, default_registry)
    assert manifest.graph_fingerprint == graph.fingerprint(default_registry)
    assert manifest.registry_version == default_registry.version
    assert manifest.catalog_hash == default_registry.catalog_hash()
    assert manifest.compatibility_version == COMPATIBILITY_VERSION
    assert manifest.backend == "torch"
    assert manifest.experimental_flags_used == ()


def test_manifest_lists_experimental_blocks_used() -> None:
    graph = ArchitectureGraph(nodes=(NodeGene(id="k", block_id="kan"),), edges=())
    manifest = manifest_for_graph(graph, default_registry)
    assert "kan" in manifest.experimental_flags_used


def test_manifest_same_graph_same_catalog_same_fingerprint() -> None:
    first = manifest_for_graph(_mlp_graph(), default_registry)
    second = manifest_for_graph(_mlp_graph(), default_registry)
    assert first.graph_fingerprint == second.graph_fingerprint
    assert first.catalog_hash == second.catalog_hash


def test_manifest_provenance_is_closed() -> None:
    manifest = manifest_for_graph(
        _mlp_graph(),
        default_registry,
        provenance=ArchitectureProvenance(source="unit-test", author="sol"),
    )
    assert manifest.provenance.source == "unit-test"
    assert manifest.provenance.author == "sol"


def test_manifest_created_at_optional() -> None:
    manifest = manifest_for_graph(_mlp_graph(), default_registry, created_at="2026-08-22T00:00:00Z")
    assert manifest.created_at == "2026-08-22T00:00:00Z"
    assert manifest_for_graph(_mlp_graph(), default_registry).created_at is None


def test_compatibility_version_is_part_of_fingerprint_payload() -> None:
    graph = _mlp_graph()
    assert graph.canonical_dict(default_registry)["compatibility_version"] == COMPATIBILITY_VERSION


def test_manifest_rejects_unsealed_registry() -> None:
    registry = make_default_registry()
    assert not registry.sealed
    with pytest.raises(RegistrySealedError):
        manifest_for_graph(_mlp_graph(), registry)


def test_build_architecture_rejects_dimension_mismatch() -> None:
    from oec.kernel.neural.architecture_build import build_architecture

    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="linear", config={"in_features": 4, "out_features": 16}),
            NodeGene(id="b", block_id="linear", config={"in_features": 8, "out_features": 2}),
        ),
        edges=(EdgeGene(source="a", target="b"),),
    )
    with pytest.raises(ArchitectureValidationError, match="dim mismatch"):
        build_architecture(graph)


def test_manifest_rejects_dimension_mismatch() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="a", block_id="linear", config={"in_features": 4, "out_features": 16}),
            NodeGene(id="b", block_id="linear", config={"in_features": 8, "out_features": 2}),
        ),
        edges=(EdgeGene(source="a", target="b"),),
    )
    with pytest.raises(ArchitectureValidationError, match="dim mismatch"):
        manifest_for_graph(graph, default_registry)


def test_manifest_rejects_invalid_graph() -> None:
    # "linear" requires out_features; this graph never validates.
    bad_graph = ArchitectureGraph(nodes=(NodeGene(id="lin", block_id="linear"),), edges=())
    with pytest.raises(ArchitectureValidationError):
        manifest_for_graph(bad_graph, default_registry)


def test_manifest_rejects_unknown_backend() -> None:
    with pytest.raises(ArchitectureValidationError, match="backend"):
        manifest_for_graph(_mlp_graph(), default_registry, backend="jax")


def test_manifest_rejects_future_backend_block() -> None:
    registry = make_default_registry()
    registry.register(
        BlockSpec(
            id="future_only",
            display_name="Future Only",
            family=NeuralFamily.FEEDFORWARD,
            category=BlockCategory.BLOCK,
            input_kinds=frozenset({TensorKind.VECTOR}),
            output_kind=TensorKind.VECTOR,
            backend_requirements=("future-xyz",),
            experimental=True,
        )
    )
    registry.seal()
    graph = ArchitectureGraph(nodes=(NodeGene(id="f", block_id="future_only"),), edges=())
    with pytest.raises(ArchitectureValidationError, match="requires backends"):
        manifest_for_graph(graph, registry, backend="torch")


def test_manifest_rejects_torch_block_without_builder() -> None:
    registry = make_default_registry()
    registry.register(
        BlockSpec(
            id="catalog_only",
            display_name="Catalog Only",
            family=NeuralFamily.FEEDFORWARD,
            category=BlockCategory.BLOCK,
            input_kinds=frozenset({TensorKind.VECTOR}),
            output_kind=TensorKind.VECTOR,
            backend_requirements=("torch",),
            experimental=True,
        )
    )
    registry.seal()
    graph = ArchitectureGraph(nodes=(NodeGene(id="c", block_id="catalog_only"),), edges=())
    with pytest.raises(ArchitectureValidationError, match="no torch builder"):
        manifest_for_graph(graph, registry, backend="torch")


def test_audit_default_registry_is_sealed_and_typed_correctly() -> None:
    report = audit_catalog(default_registry)
    assert report.valid
    assert report.errors == ()
    assert "mlp" in report.stable_ids
    assert "kan" in report.experimental_ids
    assert set(report.stable_ids).isdisjoint(report.experimental_ids)


def test_audit_flags_experimental_block_missing_backend_requirements() -> None:
    # The real catalog no longer has one (fixed as part of this fail-closed
    # pass); register a synthetic experimental block to prove the check.
    registry = make_default_registry()
    registry.register(
        BlockSpec(
            id="synthetic_experimental_no_backend",
            display_name="Synthetic Experimental",
            family=NeuralFamily.FEEDFORWARD,
            category=BlockCategory.BLOCK,
            input_kinds=frozenset({TensorKind.VECTOR}),
            output_kind=TensorKind.VECTOR,
            experimental=True,
        )
    )
    report = audit_catalog(registry)
    assert not report.valid
    assert any("missing backend_requirements" in error for error in report.errors)


def test_audit_flags_unsealed_registry() -> None:
    registry = make_default_registry()
    assert not registry.sealed
    report = audit_catalog(registry)
    assert not report.valid
    assert any("registry is not sealed" in error for error in report.errors)
    sealed_report = audit_catalog(default_registry)
    assert not any("registry is not sealed" in error for error in sealed_report.errors)


def test_audit_flags_unknown_parameter_kind() -> None:
    registry = make_default_registry()
    registry.register(
        BlockSpec(
            id="bad_kind_block",
            display_name="Bad Kind",
            family=NeuralFamily.FEEDFORWARD,
            category=BlockCategory.BLOCK,
            input_kinds=frozenset({TensorKind.VECTOR}),
            output_kind=TensorKind.VECTOR,
            parameters=(BlockParameterSpec(name="x", kind="not_a_real_kind"),),
        )
    )
    report = audit_catalog(registry)
    assert not report.valid
    assert any("unknown kind" in error for error in report.errors)


def test_audit_flags_missing_input_ports() -> None:
    registry = make_default_registry()
    registry.register(
        BlockSpec(
            id="no_ports_block",
            display_name="No Ports",
            family=NeuralFamily.FEEDFORWARD,
            category=BlockCategory.BLOCK,
            input_kinds=frozenset({TensorKind.VECTOR}),
            output_kind=TensorKind.VECTOR,
            input_ports=(),
        )
    )
    report = audit_catalog(registry)
    assert not report.valid
    assert any("no input_ports" in error for error in report.errors)


def test_audit_experimental_vs_stable_status_partitions_catalog() -> None:
    report = audit_catalog(default_registry)
    all_ids = {spec.id for spec in default_registry.list()}
    assert set(report.experimental_ids) | set(report.stable_ids) == all_ids
