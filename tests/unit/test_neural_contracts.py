"""Neural contract unit tests (no torch required)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from oec.neural.contracts import DatasetSpec, NeuralModelSpec, TrainingSpec
from oec.neural.hashing import dataset_fingerprint, model_spec_fingerprint


def test_dataset_spec_rejects_ragged_rows() -> None:
    with pytest.raises(ValidationError):
        DatasetSpec(x=[[1.0, 2.0], [1.0]], y=[0.0, 1.0])


def test_model_spec_rejects_empty_hidden() -> None:
    with pytest.raises(ValidationError):
        NeuralModelSpec(input_dim=2, hidden_dims=[])


def test_training_spec_defaults_and_fingerprint_stable() -> None:
    ds = DatasetSpec(x=[[0.0], [1.0], [2.0]], y=[0.0, 1.0, 2.0])
    model = NeuralModelSpec(input_dim=1, hidden_dims=[8, 4])
    train = TrainingSpec(seed=7)
    assert train.epochs >= 1
    h1 = dataset_fingerprint(ds.x, ds.y)
    h2 = dataset_fingerprint(ds.x, ds.y)
    assert h1 == h2
    assert len(model_spec_fingerprint(model.model_dump(mode="json"))) == 64
