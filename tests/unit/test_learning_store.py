"""L2 dataset/run persistence and L3 replay — core-safe."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from oec.learning import (
    BackendNotAvailableError,
    DatasetIntegrityError,
    FineTuneBackendName,
    LearningDataset,
    LearningRunRecord,
    ModelRef,
    TrainingConfig,
    TrainingResult,
)
from oec.learning.experiments import compute_run_identity
from oec.learning.store import (
    load_dataset,
    load_run,
    replay_learning_experiment,
    save_dataset,
    save_run,
)


def _dataset() -> LearningDataset:
    return LearningDataset(
        name="demo",
        version="1.2.3",
        records=({"text": "alpha"}, {"text": "beta"}),
    )


def _record(
    dataset: LearningDataset | None = None,
    *,
    backend: FineTuneBackendName = FineTuneBackendName.HUGGINGFACE,
) -> LearningRunRecord:
    ds = dataset or _dataset()
    model = ModelRef(model_id="local/demo", revision="abc")
    config = TrainingConfig(backend=backend, max_steps=2, seed=9)
    record = LearningRunRecord(
        run_id="run-1",
        experiment_id="learn.store",
        code_version={"git_commit": "deadbeef"},
        environment={},
        hardware={},
        dataset=ds,
        dataset_name=ds.name,
        dataset_version=ds.version,
        dataset_hash=ds.content_hash,
        model_id=model.model_id,
        model_revision=model.revision,
        backend=backend,
        config=config,
        seed=config.seed,
        result=TrainingResult(
            status="ok",
            backend=backend,
            method=config.method,
            model=model,
        ),
    )
    return record.model_copy(update={"identity_hash": compute_run_identity(record)})


def test_store_import_does_not_load_ml_packages() -> None:
    code = (
        "import sys; import oec.learning.store; "
        "print(','.join(sorted(name for name in sys.modules "
        "if name.split('.', 1)[0] in {'torch', 'transformers', 'unsloth', 'axolotl', 'art'})))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )
    assert completed.stdout.strip() == ""


def test_dataset_save_load_roundtrip(tmp_path: Path) -> None:
    dataset = _dataset()
    written = save_dataset(dataset, tmp_path)
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert set(payload) >= {"schema", "records", "content_hash"}
    assert payload["content_hash"] == dataset.content_hash
    loaded = load_dataset(tmp_path)
    assert loaded == dataset
    assert loaded.content_hash == dataset.content_hash


def test_dataset_load_rejects_hash_mismatch(tmp_path: Path) -> None:
    written = save_dataset(_dataset(), tmp_path)
    payload = json.loads(written.read_text(encoding="utf-8"))
    payload["records"][0]["text"] = "tampered"
    written.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DatasetIntegrityError):
        load_dataset(tmp_path)


def test_dataset_load_rejects_wrong_stored_hash(tmp_path: Path) -> None:
    written = save_dataset(_dataset(), tmp_path)
    payload = json.loads(written.read_text(encoding="utf-8"))
    payload["content_hash"] = "0" * 64
    written.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DatasetIntegrityError):
        load_dataset(tmp_path)


def test_dataset_load_rejects_missing_hash(tmp_path: Path) -> None:
    written = save_dataset(_dataset(), tmp_path)
    payload = json.loads(written.read_text(encoding="utf-8"))
    payload["content_hash"] = ""
    written.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DatasetIntegrityError, match="missing content_hash"):
        load_dataset(tmp_path)


def test_run_save_load_roundtrip(tmp_path: Path) -> None:
    record = _record()
    save_run(record, tmp_path)
    loaded = load_run(tmp_path)
    assert loaded == record
    assert loaded.dataset.content_hash == record.dataset.content_hash


def test_run_load_rejects_dataset_hash_mismatch(tmp_path: Path) -> None:
    written = save_run(_record(), tmp_path)
    payload = json.loads(written.read_text(encoding="utf-8"))
    payload["dataset"]["records"][0]["text"] = "tampered"
    written.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DatasetIntegrityError):
        load_run(tmp_path)


def test_replay_fail_closed_without_extras() -> None:
    record = _record(backend=FineTuneBackendName.UNSLOTH)
    with pytest.raises(BackendNotAvailableError):
        replay_learning_experiment(record)
    record = _record(backend=FineTuneBackendName.AXOLOTL)
    with pytest.raises(BackendNotAvailableError):
        replay_learning_experiment(record)


def test_replay_huggingface_fail_closed_without_transformers() -> None:
    record = _record()
    try:
        import transformers  # noqa: F401
    except ImportError:
        with pytest.raises(BackendNotAvailableError):
            replay_learning_experiment(record)
    else:
        pytest.skip("transformers installed — fail-closed path not exercised")


def test_replay_returns_backend_result_without_inventing_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record()
    captured: dict[str, object] = {}

    class _Backend:
        def finetune(
            self,
            model: ModelRef,
            dataset: LearningDataset,
            config: TrainingConfig,
        ) -> TrainingResult:
            captured["model"] = model
            captured["dataset"] = dataset
            captured["config"] = config
            return TrainingResult(
                status="ok",
                backend=config.backend,
                method=config.method,
                model=model,
                metrics={"loss": 0.42},
            )

    monkeypatch.setattr("oec.learning.store.select_backend", lambda name: _Backend())
    report = replay_learning_experiment(record)
    assert report.source_run_id == record.run_id
    assert report.comparison["identity_match"] is True
    assert report.record.result.metrics == {"loss": 0.42}
    assert report.record.source_run_id == record.run_id
    assert captured["dataset"] is record.dataset
    assert captured["config"] == record.config
    model = captured["model"]
    assert isinstance(model, ModelRef)
    assert model.model_id == record.model_id
    assert model.revision == record.model_revision
