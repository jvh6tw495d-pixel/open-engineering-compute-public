"""L1–L5 Learning layer — core-safe (no torch/transformers required)."""

from __future__ import annotations

import importlib
import sys

import pytest

from oec.learning import (
    BackendNotAvailableError,
    Benchmark,
    DatasetIntegrityError,
    DatasetKind,
    FineTuneBackendName,
    LearningDataset,
    LearningExperiment,
    MetricDirection,
    MetricSpec,
    ModelFamily,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
    compare_results,
    compute_dataset_hash,
    run_learning_experiment,
    select_backend,
    split_records,
)


def test_import_learning_does_not_load_transformers() -> None:
    sys.modules.pop("transformers", None)
    importlib.reload(importlib.import_module("oec.learning"))
    assert "transformers" not in sys.modules
    assert "unsloth" not in sys.modules
    assert "axolotl" not in sys.modules


def test_dataset_hash_is_stable_and_verified() -> None:
    rows = ({"text": "hello"}, {"text": "world"})
    ds = LearningDataset(name="demo", kind=DatasetKind.SFT, records=rows, version="1.0.0")
    assert ds.content_hash is not None
    assert len(ds.content_hash) == 64
    again = compute_dataset_hash(
        name="demo",
        kind=DatasetKind.SFT,
        version="1.0.0",
        records=rows,
        split=ds.split,
        seed=0,
    )
    assert again == ds.content_hash
    with pytest.raises(DatasetIntegrityError):
        LearningDataset(
            name="demo",
            kind=DatasetKind.SFT,
            records=rows,
            version="1.0.0",
            content_hash="0" * 64,
        )


def test_split_records_deterministic() -> None:
    rows = [{"i": i} for i in range(10)]
    a_train, a_val = split_records(rows, val_fraction=0.3, seed=7)
    b_train, b_val = split_records(rows, val_fraction=0.3, seed=7)
    assert a_train == b_train and a_val == b_val
    assert len(a_val) == 3


def test_compare_two_results_under_one_benchmark() -> None:
    bench = Benchmark(
        name="loss-protocol",
        metrics=(MetricSpec(name="loss", direction=MetricDirection.MINIMIZE),),
    )
    left = TrainingResult(
        status="ok",
        backend=FineTuneBackendName.HUGGINGFACE,
        method=TrainingMethod.LORA,
        model=ModelRef(model_id="local/demo"),
        metrics={"loss": 1.2},
    )
    right = TrainingResult(
        status="ok",
        backend=FineTuneBackendName.HUGGINGFACE,
        method=TrainingMethod.LORA,
        model=ModelRef(model_id="local/demo"),
        metrics={"loss": 0.8},
    )
    out = compare_results(bench, left, right, left_id="a", right_id="b")
    assert out["comparisons"][0]["winner"] == "b"


def test_unsloth_and_axolotl_not_in_l1_l5() -> None:
    with pytest.raises(BackendNotAvailableError):
        select_backend(FineTuneBackendName.UNSLOTH)
    with pytest.raises(BackendNotAvailableError):
        select_backend(FineTuneBackendName.AXOLOTL)


def test_huggingface_backend_fail_closed_without_transformers() -> None:
    ds = LearningDataset(
        name="sft-tiny",
        kind=DatasetKind.SFT,
        records=({"text": "alpha"}, {"text": "beta"}),
    )
    exp = LearningExperiment(
        experiment_id="learn.l5.smoke",
        model=ModelRef(model_id="sshleifer/tiny-gpt2", family=ModelFamily.TRANSFORMERS),
        dataset=ds,
        config=TrainingConfig(method=TrainingMethod.LORA, max_steps=2, seed=0),
    )
    try:
        import transformers  # noqa: F401
    except ImportError:
        with pytest.raises(BackendNotAvailableError):
            run_learning_experiment(exp)
    else:
        pytest.skip("transformers installed — fail-closed path not exercised")
