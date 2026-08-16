"""Adversarial regression tests for the L1-L5 Learning boundary."""

from __future__ import annotations

import subprocess
import sys

import pytest

from oec.learning import (
    BackendNotAvailableError,
    DatasetIntegrityError,
    LearningDataset,
    LearningExperiment,
    LearningRunRecord,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
    run_learning_experiment,
)


def test_learning_import_isolated_from_all_ml_backends() -> None:
    code = (
        "import sys; import oec.learning; "
        "print(','.join(sorted(name for name in sys.modules "
        "if name.split('.', 1)[0] in {'torch', 'transformers', 'unsloth', 'axolotl', 'art'})))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )
    assert completed.stdout.strip() == ""


def test_mutated_dataset_is_rejected_before_backend_selection() -> None:
    dataset = LearningDataset(name="demo", records=({"text": "original"},))
    dataset.records[0]["text"] = "tampered"
    experiment = LearningExperiment(
        experiment_id="learn.integrity",
        model=ModelRef(model_id="local/demo"),
        dataset=dataset,
        config=TrainingConfig(),
    )
    with pytest.raises(DatasetIntegrityError, match="changed after"):
        run_learning_experiment(experiment)


def test_dataset_hash_rejects_non_canonical_values() -> None:
    with pytest.raises(DatasetIntegrityError, match="canonical JSON"):
        LearningDataset(name="demo", records=({"opaque": object()},))


def test_run_record_preserves_reproducible_inputs() -> None:
    dataset = LearningDataset(name="demo", version="1.2.3", records=({"text": "ok"},))
    experiment = LearningExperiment(
        experiment_id="learn.snapshot",
        model=ModelRef(model_id="local/demo", revision="abc"),
        dataset=dataset,
        config=TrainingConfig(max_steps=3, seed=9),
    )
    record = LearningRunRecord(
        run_id="run-1",
        experiment_id=experiment.experiment_id,
        code_version={"git_commit": "deadbeef"},
        environment={},
        hardware={},
        dataset=dataset,
        dataset_name=dataset.name,
        dataset_version=dataset.version,
        dataset_hash=dataset.content_hash,
        model_id=experiment.model.model_id,
        model_revision=experiment.model.revision,
        backend=experiment.config.backend,
        config=experiment.config,
        seed=experiment.config.seed,
        result=TrainingResult(
            status="ok",
            backend=experiment.config.backend,
            method=experiment.config.method,
            model=experiment.model,
        ),
    )
    assert record.dataset.content_hash == dataset.content_hash
    assert record.config == experiment.config


def test_huggingface_backend_wraps_foundation_extra_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from oec.foundation import runtime
    from oec.foundation.errors import TransformersNotAvailableError

    def unavailable(_: object) -> dict[str, object]:
        raise TransformersNotAvailableError("missing extra")

    monkeypatch.setattr(runtime, "peft_train", unavailable)
    experiment = LearningExperiment(
        experiment_id="learn.l5.wrap",
        model=ModelRef(model_id="local/demo"),
        dataset=LearningDataset(name="sft-tiny", records=({"text": "alpha"},)),
        config=TrainingConfig(
            method=TrainingMethod.LORA,
            hyperparameters={"target_modules": "q_proj,v_proj"},
        ),
    )
    with pytest.raises(BackendNotAvailableError) as exc_info:
        run_learning_experiment(experiment)
    assert exc_info.value.details["error_type"] == "TransformersNotAvailableError"
