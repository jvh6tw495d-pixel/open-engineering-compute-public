"""Part A N-D0: capacity tables + runtime contracts (no torch required)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from oec.neural.runtime import (
    CheckpointRef,
    DatasetRef,
    TrainingRuntimeSpec,
    estimate_mlp_param_count,
    resolve_capacity,
    resolve_mlp_hidden_dims,
)


def test_resolve_capacity_all_families() -> None:
    for family in ("mlp", "sequence", "transformer", "gnn", "autoencoder"):
        for cap in ("tiny", "medium", "dense", "wide"):
            knobs = resolve_capacity(family, cap)  # type: ignore[arg-type]
            assert isinstance(knobs, dict)
            assert knobs


def test_resolve_capacity_arch_aliases() -> None:
    assert resolve_capacity("lstm", "dense")["hidden"] == 256
    assert resolve_capacity("gcn", "tiny")["hidden"] == 32
    assert resolve_capacity("mlp", "dense")["hidden_dims"] == [512, 512, 256, 128]


def test_resolve_mlp_hidden_dims_precedence() -> None:
    h, used = resolve_mlp_hidden_dims(capacity="dense", hidden_dims=[8, 4])
    assert h == [8, 4]
    assert used is None
    h2, used2 = resolve_mlp_hidden_dims(capacity="dense", hidden_dims=None)
    assert h2 == [512, 512, 256, 128]
    assert used2 == "dense"


def test_estimate_mlp_params() -> None:
    # 2 -> 4 -> 1: 2*4+4 + 4*1+1 = 8+4+4+1 = 17
    assert estimate_mlp_param_count(2, [4], 1) == 17


def test_training_runtime_spec_defaults() -> None:
    rt = TrainingRuntimeSpec()
    assert rt.epochs == 100
    assert rt.max_params == 5_000_000
    assert rt.lr_scheduler == "none"
    assert rt.checkpoint_storage == "json_inline"


def test_dataset_ref_inline_and_path() -> None:
    ds = DatasetRef(x=[[0.0], [1.0]], y=[0.0, 1.0])
    assert ds.format == "json_inline"
    with pytest.raises(ValidationError):
        DatasetRef(format="npy")  # missing path
    ds2 = DatasetRef(format="npy", path="/tmp/data")
    assert ds2.path == "/tmp/data"


def test_checkpoint_ref_file_requires_hash() -> None:
    with pytest.raises(ValidationError):
        CheckpointRef(storage="file", path="/tmp/m.pt")
    ref = CheckpointRef(storage="file", path="/tmp/m.pt", sha256="abc")
    assert ref.sha256 == "abc"


def test_unknown_family_raises() -> None:
    with pytest.raises(ValueError, match="unknown"):
        resolve_capacity("not_a_family", "tiny")  # type: ignore[arg-type]
