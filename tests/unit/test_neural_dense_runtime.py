"""Part A N-D1: shared train runtime + dense MLP (requires torch)."""

from __future__ import annotations

import pytest

pytest.importorskip("torch")

from oec.kernel.neural.runtime import load_state_dict_from_checkpoint  # noqa: E402
from oec.kernel.neural.training import evaluate_mlp, predict_mlp, train_mlp  # noqa: E402
from oec.neural.contracts import (  # noqa: E402
    DatasetSpec,
    DeviceSpec,
    NeuralModelSpec,
    NeuralTask,
    OptimizerName,
    OptimizerSpec,
    TrainingSpec,
)
from oec.neural.runtime import (  # noqa: E402
    TrainingRuntimeSpec,
    estimate_mlp_param_count,
    resolve_capacity,
)

pytestmark = pytest.mark.neural


def test_dense_capacity_overfits_linear() -> None:
    knobs = resolve_capacity("mlp", "dense")
    hidden = list(knobs["hidden_dims"])
    x = [[float(i)] for i in range(20)]
    y = [2.0 * i + 1.0 for i in range(20)]
    dataset = DatasetSpec(x=x, y=y, val_fraction=0.0)
    model = NeuralModelSpec(input_dim=1, hidden_dims=hidden, output_dim=1)
    est = estimate_mlp_param_count(1, hidden, 1)
    assert est > 100_000  # genuinely denser than toy [32,16]
    training = TrainingSpec(
        epochs=80,
        seed=0,
        normalize_x=True,
        early_stopping_patience=None,
        optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=0.02),
        device=DeviceSpec(device="cpu"),
    )
    runtime = TrainingRuntimeSpec(
        seed=0,
        device=DeviceSpec(device="cpu"),
        epochs=80,
        batch_size=16,
        optimizer=training.optimizer,
        lr_scheduler="cosine",
        grad_clip=1.0,
        early_stopping_patience=None,
        max_params=5_000_000,
        checkpoint_storage="json_inline",
    )
    result = train_mlp(dataset, model, training, runtime=runtime, capacity="dense")
    assert result.capacity == "dense"
    assert result.n_params is not None and result.n_params == est
    assert result.train_metrics["r_squared"] > 0.9
    assert result.runtime is not None
    assert result.runtime["lr_scheduler"] == "cosine"
    # Round-trip predict
    preds = predict_mlp([[0.0], [1.0], [2.0]], result.checkpoint, normalize=result.normalize)
    assert len(preds) == 3


def test_max_params_fail_closed() -> None:
    knobs = resolve_capacity("mlp", "wide")
    hidden = list(knobs["hidden_dims"])
    dataset = DatasetSpec(x=[[0.0], [1.0], [2.0]], y=[0.0, 1.0, 2.0], val_fraction=0.0)
    model = NeuralModelSpec(input_dim=1, hidden_dims=hidden, output_dim=1)
    training = TrainingSpec(epochs=2, seed=0, early_stopping_patience=None)
    runtime = TrainingRuntimeSpec(
        seed=0,
        epochs=2,
        max_params=1000,  # far below wide MLP
        early_stopping_patience=None,
    )
    with pytest.raises(ValueError, match="max_params"):
        train_mlp(dataset, model, training, runtime=runtime, capacity="wide")


def test_file_checkpoint_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OEC_CACHE_DIR", str(tmp_path))
    x = [[float(i)] for i in range(12)]
    y = [float(i) for i in range(12)]
    dataset = DatasetSpec(x=x, y=y, val_fraction=0.0)
    model = NeuralModelSpec(input_dim=1, hidden_dims=[16], output_dim=1)
    training = TrainingSpec(epochs=30, seed=1, early_stopping_patience=None, normalize_x=True)
    runtime = TrainingRuntimeSpec(
        seed=1,
        epochs=30,
        early_stopping_patience=None,
        checkpoint_storage="file",
    )
    result = train_mlp(dataset, model, training, runtime=runtime, capacity=None, run_id="test-run")
    assert result.checkpoint.get("storage") == "file"
    assert result.checkpoint_ref is not None
    assert result.checkpoint_ref["sha256"]
    preds = predict_mlp([[3.0]], result.checkpoint, normalize=result.normalize)
    assert len(preds) == 1


def test_file_checkpoint_rejects_sha256_tamper(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OEC_CACHE_DIR", str(tmp_path))
    result = train_mlp(
        DatasetSpec(x=[[0.0], [1.0]], y=[0.0, 1.0], val_fraction=0.0),
        NeuralModelSpec(input_dim=1, hidden_dims=[2], output_dim=1),
        TrainingSpec(epochs=2, seed=2, early_stopping_patience=None),
        runtime=TrainingRuntimeSpec(seed=2, epochs=2, checkpoint_storage="file"),
        run_id="tamper",
    )
    from pathlib import Path

    Path(result.checkpoint["path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="sha256.*mismatch"):
        predict_mlp([[0.0]], result.checkpoint)


def test_versioned_json_inline_tamper_rejects_predict_and_evaluate() -> None:
    result = train_mlp(
        DatasetSpec(x=[[0.0], [1.0]], y=[0.0, 1.0], val_fraction=0.0),
        NeuralModelSpec(input_dim=1, hidden_dims=[2], output_dim=1),
        TrainingSpec(epochs=2, seed=2, early_stopping_patience=None),
        runtime=TrainingRuntimeSpec(seed=2, epochs=2, checkpoint_storage="json_inline"),
    )
    checkpoint = dict(result.checkpoint)
    checkpoint["state_dict"] = dict(checkpoint["state_dict"])
    first_key = next(iter(checkpoint["state_dict"]))
    checkpoint["state_dict"][first_key][0][0] += 1.0

    with pytest.raises(ValueError, match="sha256.*mismatch"):
        predict_mlp([[0.0]], checkpoint)
    with pytest.raises(ValueError, match="sha256.*mismatch"):
        evaluate_mlp([[0.0]], [0.0], checkpoint, task=NeuralTask.REGRESSION)


def test_versioned_json_inline_checkpoint_rejects_missing_digest() -> None:
    result = train_mlp(
        DatasetSpec(x=[[0.0], [1.0]], y=[0.0, 1.0], val_fraction=0.0),
        NeuralModelSpec(input_dim=1, hidden_dims=[2], output_dim=1),
        TrainingSpec(epochs=2, seed=2, early_stopping_patience=None),
        runtime=TrainingRuntimeSpec(seed=2, epochs=2, checkpoint_storage="json_inline"),
    )
    checkpoint = dict(result.checkpoint)
    checkpoint.pop("sha256")

    with pytest.raises(ValueError, match="required sha256"):
        load_state_dict_from_checkpoint(checkpoint)


def test_json_inline_checkpoint_rejects_stripped_version_fields() -> None:
    result = train_mlp(
        DatasetSpec(x=[[0.0], [1.0]], y=[0.0, 1.0], val_fraction=0.0),
        NeuralModelSpec(input_dim=1, hidden_dims=[2], output_dim=1),
        TrainingSpec(epochs=2, seed=2, early_stopping_patience=None),
        runtime=TrainingRuntimeSpec(seed=2, epochs=2, checkpoint_storage="json_inline"),
    )
    checkpoint = dict(result.checkpoint)
    checkpoint.pop("storage")
    checkpoint.pop("checkpoint_format_version")
    first_key = next(iter(checkpoint["state_dict"]))
    checkpoint["state_dict"] = dict(checkpoint["state_dict"])
    checkpoint["state_dict"][first_key][0][0] += 1.0

    with pytest.raises(ValueError, match="requires versioned storage"):
        predict_mlp([[0.0]], checkpoint)


def test_explicit_json_inline_checkpoint_rejects_missing_format_version() -> None:
    result = train_mlp(
        DatasetSpec(x=[[0.0], [1.0]], y=[0.0, 1.0], val_fraction=0.0),
        NeuralModelSpec(input_dim=1, hidden_dims=[2], output_dim=1),
        TrainingSpec(epochs=2, seed=2, early_stopping_patience=None),
        runtime=TrainingRuntimeSpec(seed=2, epochs=2, checkpoint_storage="json_inline"),
    )
    checkpoint = dict(result.checkpoint)
    checkpoint.pop("checkpoint_format_version")

    with pytest.raises(ValueError, match="checkpoint_format_version"):
        load_state_dict_from_checkpoint(checkpoint)


def test_file_checkpoint_rejects_unconfined_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OEC_CACHE_DIR", str(tmp_path / "cache"))
    checkpoint = {"storage": "file", "path": str(tmp_path / "outside.pt"), "sha256": "0" * 64}
    with pytest.raises(ValueError, match="outside.*cache root"):
        load_state_dict_from_checkpoint(checkpoint)


def test_file_checkpoint_loads_with_weights_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OEC_CACHE_DIR", str(tmp_path))
    result = train_mlp(
        DatasetSpec(x=[[0.0], [1.0]], y=[0.0, 1.0], val_fraction=0.0),
        NeuralModelSpec(input_dim=1, hidden_dims=[2], output_dim=1),
        TrainingSpec(epochs=2, seed=2, early_stopping_patience=None),
        runtime=TrainingRuntimeSpec(seed=2, epochs=2, checkpoint_storage="file"),
        run_id="safe-load",
    )
    import torch

    real_load = torch.load
    seen: dict[str, object] = {}

    def tracking_load(*args, **kwargs):
        seen.update(kwargs)
        return real_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", tracking_load)
    predict_mlp([[0.0]], result.checkpoint)
    assert seen["weights_only"] is True
