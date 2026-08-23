"""Zip v0.1 leftover catalog (glu, conv3d, hybrid KAN, spiking, macros). Core-safe."""

from __future__ import annotations

import pytest

from oec.neural.architecture import (
    ArchitectureGraph,
    EdgeGene,
    NodeGene,
    check_connection,
    default_registry,
    validate_for_backend,
)
from oec.neural.architecture.types import NeuralFamily

_ZIP_IDS = (
    "glu",
    "residual_conv",
    "conv3d",
    "hybrid_kan",
    "lif_spike",
    "residual_stack",
    "bottleneck",
    "inception",
    "dense_block",
    "fusion",
    "message_passing_stack",
    "encoder_decoder",
    "vae",
    "gan_generator",
    "gan_discriminator",
    "moe",
    "siamese",
    "diffusion_denoiser",
    "global_avg_pool_3d",
)


def test_catalog_version_0_2_5() -> None:
    assert default_registry.version == "0.2.5"


def test_zip_ids_registered() -> None:
    ids = {spec.id for spec in default_registry.list()}
    assert [block_id for block_id in _ZIP_IDS if block_id not in ids] == []


def test_zip_blocks_declare_backend() -> None:
    for block_id in _ZIP_IDS:
        spec = default_registry.get(block_id)
        if spec.category.value == "adapter":
            continue
        assert spec.backend_requirements, block_id


def test_spiking_family_has_lif() -> None:
    specs = default_registry.by_family(NeuralFamily.SPIKING)
    assert any(spec.id == "lif_spike" for spec in specs)


def test_conv2d_still_cannot_feed_kan() -> None:
    result = check_connection(
        default_registry.get("conv2d"),
        default_registry.get("kan"),
        default_registry,
    )
    assert result.compatible is False
    assert "global_avg_pool_2d" in result.suggested_adapters


def test_conv3d_gap3d_vector_is_compatible() -> None:
    conv = check_connection(
        default_registry.get("conv3d"),
        default_registry.get("global_avg_pool_3d"),
        default_registry,
    )
    pool = check_connection(
        default_registry.get("global_avg_pool_3d"),
        default_registry.get("hybrid_kan"),
        default_registry,
    )
    assert conv.compatible
    assert pool.compatible


def test_fusion_and_siamese_need_named_ports() -> None:
    assert default_registry.get("fusion").input_ports == ("a", "b")
    assert default_registry.get("siamese").input_ports == ("left", "right")


def test_glu_manifests_torch() -> None:
    graph = ArchitectureGraph(
        nodes=(NodeGene(id="g", block_id="glu", config={"in_features": 8, "hidden_dim": 16}),),
        edges=(),
    )
    report = validate_for_backend(graph, "torch", default_registry)
    assert report.valid, report.errors


def test_jax_backend_is_known_and_linear_ok() -> None:
    graph = ArchitectureGraph(
        nodes=(NodeGene(id="l", block_id="linear", config={"in_features": 4, "out_features": 2}),),
        edges=(),
    )
    report = validate_for_backend(graph, "jax", default_registry)
    assert report.valid, report.errors


def test_jax_rejects_gnn() -> None:
    graph = ArchitectureGraph(
        nodes=(NodeGene(id="g", block_id="gcn", config={"input_size": 4, "hidden_dim": 8}),),
        edges=(),
    )
    report = validate_for_backend(graph, "jax", default_registry)
    assert not report.valid
    assert any("jax" in err for err in report.errors)


def test_siamese_named_join_is_a7() -> None:
    graph = ArchitectureGraph(
        nodes=(
            NodeGene(id="l", block_id="linear", config={"in_features": 4, "out_features": 8}),
            NodeGene(id="r", block_id="linear", config={"in_features": 4, "out_features": 8}),
            NodeGene(
                id="s",
                block_id="siamese",
                config={"in_features": 8, "hidden_dim": 8, "out_features": 1},
            ),
        ),
        edges=(
            EdgeGene(source="l", target="s", target_port="left"),
            EdgeGene(source="r", target="s", target_port="right"),
        ),
    )
    report = validate_for_backend(graph, "torch", default_registry)
    assert report.valid, report.errors


def test_build_architecture_jax_fails_closed_without_jax() -> None:
    pytest.importorskip("oec.kernel.neural.architecture_build")
    from oec.kernel.neural.architecture_build import build_architecture
    from oec.kernel.neural.errors import JaxNotAvailableError

    graph = ArchitectureGraph(
        nodes=(NodeGene(id="l", block_id="linear", config={"in_features": 4, "out_features": 2}),),
        edges=(),
    )
    try:
        import jax  # noqa: F401
    except ImportError:
        with pytest.raises(JaxNotAvailableError):
            build_architecture(graph, backend="jax")
        return
    module = build_architecture(graph, backend="jax")
    import jax.numpy as jnp
    from jax import random

    x = jnp.ones((3, 4))
    params = module.init(random.PRNGKey(0), x)
    out = module.apply(params, x)
    assert out.shape == (3, 2)
