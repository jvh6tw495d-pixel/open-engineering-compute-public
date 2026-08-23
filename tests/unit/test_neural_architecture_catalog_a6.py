"""Wave A6 expanded block catalog (ADR 0047). Core-safe."""

from __future__ import annotations

from oec.neural.architecture import check_connection, default_registry
from oec.neural.architecture.types import NeuralFamily, TensorKind

_A6_IDS = (
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
    "deeponet",
    "pinn_motif",
)


def test_registry_version_a6() -> None:
    assert default_registry.version == "0.2.1"


def test_all_a6_ids_registered() -> None:
    ids = {spec.id for spec in default_registry.list()}
    missing = [block_id for block_id in _A6_IDS if block_id not in ids]
    assert missing == []


def test_each_a6_block_declares_backend() -> None:
    for block_id in _A6_IDS:
        spec = default_registry.get(block_id)
        assert spec.backend_requirements, block_id


def test_scientific_families_present() -> None:
    assert default_registry.by_family(NeuralFamily.CONTINUOUS)
    assert default_registry.by_family(NeuralFamily.NEURAL_OPERATOR)
    assert default_registry.by_family(NeuralFamily.PHYSICS_INFORMED)


def test_se_after_conv2d_is_compatible() -> None:
    result = check_connection(
        default_registry.get("conv2d"),
        default_registry.get("squeeze_excitation"),
        default_registry,
    )
    assert result.compatible


def test_highway_vector_to_vector() -> None:
    ids = {
        spec.id
        for spec in default_registry.compatible_blocks(
            input_kind=TensorKind.VECTOR,
            output_kind=TensorKind.VECTOR,
        )
    }
    assert "highway" in ids
    assert "neural_ode" in ids
    assert "pinn_motif" in ids


def test_cross_attention_rejects_unary_edge() -> None:
    result = check_connection(
        default_registry.get("transformer_encoder"),
        default_registry.get("cross_attention"),
        default_registry,
    )
    assert not result.compatible
    assert "named ports" in result.reason


def test_geglu_is_rank_preserving_sequence() -> None:
    spec = default_registry.get("geglu")
    assert spec.input_kinds == frozenset({TensorKind.SEQUENCE})
    assert spec.output_kind == TensorKind.SEQUENCE
    assert not spec.accepts(TensorKind.VECTOR)


def test_fno_is_split_by_rank() -> None:
    fno = default_registry.get("fno")
    fno_2d = default_registry.get("fno_2d")
    assert fno.input_kinds == frozenset({TensorKind.FEATURE_MAP_1D})
    assert fno.output_kind == TensorKind.FEATURE_MAP_1D
    assert fno_2d.input_kinds == frozenset({TensorKind.FEATURE_MAP_2D})
    assert fno_2d.output_kind == TensorKind.FEATURE_MAP_2D
    assert not fno.accepts(TensorKind.FEATURE_MAP_2D)
