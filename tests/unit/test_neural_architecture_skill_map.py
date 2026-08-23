"""A5 skill → ArchitectureGraph mapping (ADR 0047). No torch."""

from __future__ import annotations

import pytest

from oec.neural.architecture import default_registry
from oec.neural.architecture.errors import ArchitectureValidationError, UnknownBlockError
from oec.neural.architecture.skill_map import graph_for_skill, mapped_skill_ids


def test_mapped_ids_cover_family_skills() -> None:
    ids = set(mapped_skill_ids())
    assert "neural.mlp.regressor" in ids
    assert "neural.cnn1d" in ids
    assert "neural.gcn" in ids
    assert "neural.transformer.encoder" in ids


def test_mlp_graph_validates() -> None:
    graph = graph_for_skill("neural.mlp.classifier")
    report = graph.validate_graph(default_registry)
    assert report.valid, report.errors
    assert graph.nodes[0].block_id == "mlp"


def test_cnn1d_uses_explicit_adapter() -> None:
    graph = graph_for_skill("neural.cnn1d")
    blocks = [node.block_id for node in graph.nodes]
    assert blocks == ["conv1d", "global_avg_pool_1d", "mlp"]
    assert graph.validate_graph(default_registry).valid


def test_gnn_chain_validates() -> None:
    graph = graph_for_skill("neural.gat")
    report = graph.validate_graph(default_registry)
    assert report.valid, report.errors
    assert [n.block_id for n in graph.nodes][-1] == "mlp"


def test_unknown_skill_fails_closed() -> None:
    with pytest.raises(UnknownBlockError, match="no architecture mapping"):
        graph_for_skill("neural.not_a_skill")


def test_all_mapped_graphs_validate() -> None:
    for skill_id in mapped_skill_ids():
        report = graph_for_skill(skill_id).validate_graph(default_registry)
        assert report.valid, (skill_id, report.errors)


def test_mlp_classifier_translates_architectural_inputs() -> None:
    graph = graph_for_skill(
        "neural.mlp.classifier",
        {
            "x": [[0.0, 1.0, 2.0, 3.0], [1.0, 0.0, 1.0, 0.0]],
            "hidden_dims": [32, 16],
            "n_classes": 3,
            "activation": "relu",
            "epochs": 5,
        },
    )
    cfg = dict(graph.nodes[0].config)
    assert cfg["in_features"] == 4
    assert cfg["hidden_dim"] == 32
    assert cfg["out_features"] == 3
    assert cfg["activation"] == "relu"
    assert "epochs" not in cfg
    assert graph.validate_graph(default_registry).valid


def test_unmappable_activation_fails_closed() -> None:
    with pytest.raises(ArchitectureValidationError, match="not representable"):
        graph_for_skill("neural.mlp.classifier", {"activation": "sigmoid"})


def test_lstm_translates_hidden_and_layers() -> None:
    graph = graph_for_skill(
        "neural.lstm",
        {
            "x": [[[0.0, 1.0], [1.0, 0.0]], [[0.0, 1.0], [1.0, 0.0]]],
            "hidden": 32,
            "n_layers": 2,
            "n_classes": 1,
        },
    )
    body = next(node for node in graph.nodes if node.block_id == "lstm")
    cfg = dict(body.config)
    assert cfg["input_size"] == 2
    assert cfg["hidden_dim"] == 32
    assert cfg["n_layers"] == 2
    assert graph.validate_graph(default_registry).valid


def test_transformer_translates_nheads_to_nhead() -> None:
    graph = graph_for_skill(
        "neural.transformer.encoder",
        {"d_model": 32, "n_heads": 4, "n_layers": 2, "ff_dim": 64},
    )
    body = next(node for node in graph.nodes if node.block_id == "transformer_encoder")
    cfg = dict(body.config)
    assert cfg["d_model"] == 32
    assert cfg["nhead"] == 4
    assert cfg["num_layers"] == 2
    assert cfg["dim_feedforward"] == 64
    assert graph.validate_graph(default_registry).valid
