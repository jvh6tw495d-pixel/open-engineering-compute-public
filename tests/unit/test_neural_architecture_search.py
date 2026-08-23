"""IR-governed NAS (ADR 0047 wave A8+). Core-safe — no GPU, no TITAN, no free Python fitness."""

from __future__ import annotations

import subprocess
import sys

import pytest

from oec.neural.architecture import default_registry
from oec.neural.architecture.errors import ArchitectureValidationError
from oec.neural.architecture.search import _estimate_block_params, search_graphs


def test_import_does_not_require_torch() -> None:
    import oec.neural.architecture.search as search_mod

    assert "torch" not in getattr(search_mod, "__dict__", {})


def test_search_import_does_not_load_torch_in_clean_process() -> None:
    code = (
        "import sys; "
        "assert 'torch' not in sys.modules; "
        "import oec.neural.architecture.search as search_mod; "
        "assert 'torch' not in sys.modules; "
        "assert 'torch' not in search_mod.__dict__"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("family", ["mlp", "cnn1d", "lstm"])
def test_candidates_are_all_valid_ir_graphs(family: str) -> None:
    result = search_graphs(
        family,  # type: ignore[arg-type]
        in_features=4,
        out_features=2,
        widths=(8, 16),
        depths=(1, 2),
    )
    assert result.candidates_rejected == ()
    assert result.candidates_evaluated == 4
    assert result.best is not None
    assert result.best.graph.validate_graph(default_registry).valid


def test_objective_is_always_param_count_estimate() -> None:
    result = search_graphs("mlp", in_features=4, out_features=1, widths=(4, 64), depths=(1,))
    assert result.objective == "param_count_estimate"
    # A 4->4->1 chain has fewer params than 4->64->1; the estimator must prefer it.
    assert result.best is not None
    assert result.best.width == 4


def test_unknown_objective_fails_closed() -> None:
    with pytest.raises(ArchitectureValidationError, match="objective"):
        search_graphs("mlp", objective="mystery")  # type: ignore[arg-type]


def test_trainer_kwarg_is_rejected() -> None:
    """The API has no callback surface at all: a stray trainer= kwarg is a TypeError."""
    with pytest.raises(TypeError):
        search_graphs("mlp", trainer=lambda graph: 0.0)  # type: ignore[call-arg]


def test_unknown_family_fails_closed() -> None:
    with pytest.raises(ArchitectureValidationError, match="unknown search family"):
        search_graphs("not_a_family")  # type: ignore[arg-type]


def test_result_includes_best_fingerprint_and_manifest() -> None:
    result = search_graphs("mlp", in_features=4, out_features=1, widths=(8,), depths=(1,))
    assert result.best is not None
    assert result.best_manifest is not None
    assert result.best_manifest.graph_fingerprint == result.best.graph.fingerprint(default_registry)
    assert result.best_manifest.registry_version == default_registry.version


def test_cnn1d_and_lstm_candidates_use_closed_widths_and_depths() -> None:
    result = search_graphs("cnn1d", in_features=3, out_features=2, widths=(8,), depths=(1, 2))
    assert result.candidates_evaluated == 2
    lstm_result = search_graphs("lstm", in_features=3, out_features=2, widths=(8,), depths=(1,))
    assert lstm_result.candidates_evaluated == 1
    assert lstm_result.best is not None
    assert [n.block_id for n in lstm_result.best.graph.nodes] == ["lstm", "sequence_pool", "mlp"]


def test_rejects_empty_widths() -> None:
    with pytest.raises(ArchitectureValidationError, match="widths"):
        search_graphs("mlp", widths=())


def test_rejects_non_int_or_bool_widths() -> None:
    with pytest.raises(ArchitectureValidationError, match="widths"):
        search_graphs("mlp", widths=(8.0,))  # type: ignore[arg-type]
    with pytest.raises(ArchitectureValidationError, match="widths"):
        search_graphs("mlp", widths=(True,))  # type: ignore[arg-type]


def test_rejects_zero_or_negative_depths() -> None:
    with pytest.raises(ArchitectureValidationError, match="depths"):
        search_graphs("mlp", depths=(0,))
    with pytest.raises(ArchitectureValidationError, match="depths"):
        search_graphs("mlp", depths=(-1,))


def test_rejects_non_int_in_features_and_out_features() -> None:
    with pytest.raises(ArchitectureValidationError, match="in_features"):
        search_graphs("mlp", in_features=4.5)  # type: ignore[arg-type]
    with pytest.raises(ArchitectureValidationError, match="out_features"):
        search_graphs("mlp", out_features=0)


@pytest.mark.neural
@pytest.mark.parametrize("n_layers", [1, 2])
def test_lstm_param_estimate_matches_torch(n_layers: int) -> None:
    pytest.importorskip("torch")
    import torch.nn as nn

    hidden = 6
    in_sz = 5
    model = nn.LSTM(in_sz, hidden, num_layers=n_layers, batch_first=True)
    actual = sum(p.numel() for p in model.parameters())
    estimate = _estimate_block_params(
        "lstm", {"input_size": in_sz, "hidden_dim": hidden, "n_layers": n_layers}
    )
    assert estimate == actual


@pytest.mark.neural
@pytest.mark.parametrize("n_layers", [1, 2])
def test_gru_param_estimate_matches_torch(n_layers: int) -> None:
    pytest.importorskip("torch")
    import torch.nn as nn

    hidden = 6
    in_sz = 5
    model = nn.GRU(in_sz, hidden, num_layers=n_layers, batch_first=True)
    actual = sum(p.numel() for p in model.parameters())
    estimate = _estimate_block_params(
        "gru", {"input_size": in_sz, "hidden_dim": hidden, "n_layers": n_layers}
    )
    assert estimate == actual
