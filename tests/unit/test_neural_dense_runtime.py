"""Part A N-D1: shared train runtime + dense MLP (requires torch)."""

from __future__ import annotations

import pytest

pytest.importorskip("torch")

from oec.kernel.neural.training import predict_mlp, train_mlp  # noqa: E402
from oec.neural.contracts import (  # noqa: E402
    DatasetSpec,
    DeviceSpec,
    NeuralModelSpec,
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
