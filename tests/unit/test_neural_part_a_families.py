"""Part A complete: capacity + shared runtime across neural families."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("torch")

from oec.kernel.neural.autoencoder import train_autoencoder  # noqa: E402
from oec.kernel.neural.gnn import train_gnn  # noqa: E402
from oec.kernel.neural.runtime import load_dataset_arrays  # noqa: E402
from oec.kernel.neural.sequences import train_sequence_model  # noqa: E402
from oec.kernel.neural.transformer import train_transformer_sequence  # noqa: E402
from oec.neural.contracts import DeviceSpec, OptimizerName, OptimizerSpec  # noqa: E402
from oec.neural.runtime import TrainingRuntimeSpec, resolve_capacity  # noqa: E402

pytestmark = pytest.mark.neural


def test_sequence_capacity_medium_reports_params() -> None:
    knobs = resolve_capacity("lstm", "medium")
    # small synthetic sequences
    rng = np.random.default_rng(0)
    x = rng.normal(size=(24, 8, 2)).tolist()
    y = rng.normal(size=24).tolist()
    rt = TrainingRuntimeSpec(
        seed=0,
        epochs=15,
        batch_size=8,
        optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=1e-2),
        early_stopping_patience=None,
        checkpoint_storage="json_inline",
    )
    out = train_sequence_model(
        x,
        y,
        arch="lstm",
        hidden=int(knobs["hidden"]),
        n_layers=int(knobs["n_layers"]),
        runtime=rt,
        capacity="medium",
    )
    assert out["capacity"] == "medium"
    assert out["n_params"] is not None and out["n_params"] > 1000
    assert "train_metrics" in out
    assert out["checkpoint"].get("storage") == "json_inline"


def test_transformer_capacity_tiny() -> None:
    knobs = resolve_capacity("transformer", "tiny")
    rng = np.random.default_rng(1)
    x = rng.normal(size=(16, 6, 3)).tolist()
    y = rng.normal(size=16).tolist()
    rt = TrainingRuntimeSpec(
        seed=1,
        epochs=8,
        batch_size=8,
        optimizer=OptimizerSpec(name=OptimizerName.ADAMW, lr=1e-3),
        early_stopping_patience=None,
    )
    out = train_transformer_sequence(
        x,
        y,
        d_model=int(knobs["d_model"]),
        n_heads=int(knobs["n_heads"]),
        n_layers=int(knobs["n_layers"]),
        ff_dim=int(knobs["ff_dim"]),
        runtime=rt,
        capacity="tiny",
    )
    assert out["n_params"] > 0
    assert out["capacity"] == "tiny"


def test_gnn_capacity_and_runtime() -> None:
    knobs = resolve_capacity("gcn", "tiny")
    # 4-node path graph
    node_features = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [0.5, 0.5]]
    edge_index = [[0, 1, 2], [1, 2, 3]]
    y = [0.0, 1.0, 0.5, 0.25]
    rt = TrainingRuntimeSpec(
        seed=0,
        epochs=20,
        optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=1e-2),
        early_stopping_patience=None,
    )
    out = train_gnn(
        node_features,
        edge_index,
        y,
        arch="gcn",
        hidden=int(knobs["hidden"]),
        n_layers=int(knobs["n_layers"]),
        runtime=rt,
        capacity="tiny",
    )
    assert out["n_params"] > 0
    assert out["capacity"] == "tiny"


def test_autoencoder_capacity_dense_mse() -> None:
    knobs = resolve_capacity("autoencoder", "medium")
    rng = np.random.default_rng(2)
    x = rng.normal(size=(32, 8)).tolist()
    rt = TrainingRuntimeSpec(
        seed=2,
        epochs=25,
        batch_size=8,
        early_stopping_patience=None,
        device=DeviceSpec(device="cpu"),
    )
    out = train_autoencoder(
        x,
        latent_dim=int(knobs["latent_dim"]),
        hidden_dims=list(knobs["hidden_dims"]),
        runtime=rt,
        capacity="medium",
    )
    assert out["capacity"] == "medium"
    assert out["n_params"] > 0
    assert out["train_metrics"]["mse"] >= 0.0


def test_npy_dataset_load(tmp_path) -> None:
    x = np.arange(20, dtype=np.float64).reshape(10, 2)
    y = np.arange(10, dtype=np.float64)
    d = tmp_path / "ds"
    d.mkdir()
    np.save(d / "x.npy", x)
    np.save(d / "y.npy", y)
    xl, yl = load_dataset_arrays(x=None, y=None, path=str(d), fmt="npy")
    assert xl.shape == (10, 2)
    assert yl.shape == (10,)
