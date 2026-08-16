"""Stress and adversarial tests for oec.learning — no invented metrics."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from oec.learning import (
    BackendNotAvailableError,
    DatasetIntegrityError,
    FineTuneBackendName,
    LearningDataset,
    LearningError,
    ModelRef,
    RewardSpec,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
    WorkerPipeline,
    default_worker_dataset,
    distill,
    execution_result_reward,
    execution_result_scores,
    load_dataset,
    replay_learning_experiment,
    save_dataset,
)
from oec.learning.backends import huggingface as huggingface_mod
from oec.learning.datasets import DatasetKind, texts_from_sft
from oec.learning.distillation import DistillationConfig
from oec.learning.experiments import LearningRunRecord, compute_run_identity
from oec.learning.pipeline import WorkerStage
from oec.learning.store import ReplayReport


def _ok(model: ModelRef, config: TrainingConfig) -> TrainingResult:
    return TrainingResult(
        status="ok",
        backend=config.backend,
        method=config.method,
        model=model,
        metrics={"loss": 0.1},
        artifact=None,
        message="stress-stub",
    )


def test_import_stays_core_safe_under_repeated_import() -> None:
    import subprocess
    import sys

    code = (
        "import oec.learning as a; import oec.learning as b; "
        "print(a is b); "
        "print(','.join(sorted(n for n in __import__('sys').modules "
        "if n.split('.',1)[0] in {'torch','transformers','unsloth','axolotl','art'})))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )
    out = completed.stdout.replace("\r\n", "\n")
    assert out.startswith("True\n")
    leaked = out.split("\n", 1)[1].strip()
    assert leaked == ""


def test_dataset_hash_stable_across_200_rebuilds() -> None:
    records = tuple({"text": f"row-{i}", "n": i} for i in range(50))
    first = LearningDataset(name="stress", records=records, version="9.0.0")
    for _ in range(200):
        again = LearningDataset(name="stress", records=records, version="9.0.0")
        assert again.content_hash == first.content_hash
    first.records[3]["text"] = "mutated"
    with pytest.raises(DatasetIntegrityError):
        first.verify_integrity()


def test_persist_roundtrip_large_dataset(tmp_path: Path) -> None:
    records = tuple({"text": f"x{i}" * 20, "i": i} for i in range(400))
    dataset = LearningDataset(name="bulk", records=records)
    save_dataset(dataset, tmp_path)
    loaded = load_dataset(tmp_path)
    assert loaded.content_hash == dataset.content_hash
    assert len(loaded.records) == 400
    loaded.records[-1]["text"] = "tamper"
    with pytest.raises(DatasetIntegrityError):
        loaded.verify_integrity()


def test_reward_never_increases_with_more_tokens_or_latency() -> None:
    spec = RewardSpec(correct=0.0, units=0.0, constraints=0.0, tokens=1.0, latency=1.0)
    rng = random.Random(0)
    for _ in range(80):
        budget = rng.uniform(10.0, 200.0)
        low = rng.uniform(0.0, budget)
        high = low + rng.uniform(0.1, budget)
        cheap = {
            "status": "ok",
            "tokens": low,
            "token_budget": budget,
            "latency": low,
            "latency_budget": budget,
        }
        expensive = {
            "status": "ok",
            "tokens": high,
            "token_budget": budget,
            "latency": high,
            "latency_budget": budget,
        }
        assert execution_result_reward(cheap, spec) >= execution_result_reward(expensive, spec)


def test_missing_telemetry_never_beats_measured_zero() -> None:
    spec = RewardSpec(correct=0.0, units=0.0, constraints=0.0, tokens=2.0, latency=2.0)
    missing = execution_result_reward({"status": "ok"}, spec)
    measured_zero = execution_result_reward({"status": "ok", "tokens": 0.0, "latency": 0.0}, spec)
    assert missing == 0.0
    assert measured_zero == pytest.approx(4.0)
    assert measured_zero > missing


def test_negative_consumption_is_rejected() -> None:
    with pytest.raises(ValueError):
        execution_result_scores({"status": "ok", "tokens": -1.0})


def test_texts_from_sft_rejects_unknown_and_partial_rows() -> None:
    with pytest.raises(DatasetIntegrityError):
        texts_from_sft(LearningDataset(name="bad", records=({"foo": 1},)))
    with pytest.raises(DatasetIntegrityError):
        texts_from_sft(LearningDataset(name="half", records=({"prompt": "only"},)))


def test_worker_pipeline_twenty_stages_derives_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _finetune(
        self: object, model: ModelRef, dataset: LearningDataset, config: TrainingConfig
    ) -> TrainingResult:
        return _ok(model, config)

    monkeypatch.setattr(huggingface_mod.HuggingFaceBackend, "finetune", _finetune)
    stages = tuple(
        WorkerStage(name=f"s{i}", method=TrainingMethod.LORA, backend="huggingface")
        for i in range(20)
    )
    pipe = WorkerPipeline(
        model=ModelRef(model_id="tinyllama/tiny"),
        dataset=default_worker_dataset(),
        stages=stages,
    )
    out = pipe.run(experiment_id="stress.20")
    assert out["status"] == "ok"
    assert len(out["records"]) == 20


def test_worker_pipeline_incomplete_stage_is_not_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _finetune(
        self: object, model: ModelRef, dataset: LearningDataset, config: TrainingConfig
    ) -> TrainingResult:
        return TrainingResult(
            status="incomplete",
            backend=config.backend,
            method=config.method,
            model=model,
        )

    monkeypatch.setattr(huggingface_mod.HuggingFaceBackend, "finetune", _finetune)
    pipe = WorkerPipeline(
        model=ModelRef(model_id="tinyllama/tiny"),
        dataset=default_worker_dataset(),
        stages=(WorkerStage(name="one", method=TrainingMethod.LORA, backend="huggingface"),),
    )
    assert pipe.run()["status"] == "degraded"


def test_unknown_backend_and_art_without_episodes_fail() -> None:
    ds = default_worker_dataset()
    model = ModelRef(model_id="tinyllama/tiny")
    with pytest.raises(BackendNotAvailableError):
        WorkerPipeline(
            model=model,
            dataset=ds,
            stages=(WorkerStage(name="x", method=TrainingMethod.LORA, backend="nope"),),
        ).run()
    with pytest.raises(LearningError, match="episodes"):
        WorkerPipeline(
            model=model,
            dataset=ds,
            stages=(WorkerStage(name="rl", method=TrainingMethod.SFT, backend="art"),),
        ).run()


def test_distill_stress_rejects_text_and_missing_checkpoint() -> None:
    try:
        import torch  # noqa: F401
    except ImportError:
        pytest.skip("torch missing")
    text = LearningDataset(name="t", kind=DatasetKind.SFT, records=({"text": "a"}, {"text": "b"}))
    tab = LearningDataset(
        name="tab",
        kind=DatasetKind.DISTILLATION,
        records=({"x": [1.0], "y": 1.0}, {"x": [2.0], "y": 2.0}),
    )
    teacher = ModelRef(model_id="t")
    student = ModelRef(model_id="s")
    with pytest.raises(LearningError):
        distill(teacher=teacher, student=student, dataset=text)
    with pytest.raises(LearningError, match="teacher_checkpoint"):
        distill(teacher=teacher, student=student, dataset=tab, config=DistillationConfig())


def test_replay_identity_survives_label_change(monkeypatch: pytest.MonkeyPatch) -> None:
    dataset = default_worker_dataset()
    config = TrainingConfig(seed=4)
    model = ModelRef(model_id="tinyllama/tiny")
    record = LearningRunRecord(
        run_id="a",
        experiment_id="orig",
        code_version={},
        environment={},
        hardware={},
        dataset=dataset,
        dataset_name=dataset.name,
        dataset_version=dataset.version,
        dataset_hash=dataset.content_hash,
        model_id=model.model_id,
        model_revision=None,
        backend=FineTuneBackendName.HUGGINGFACE,
        config=config,
        seed=4,
        result=_ok(model, config),
    )
    record = record.model_copy(update={"identity_hash": compute_run_identity(record)})

    def _finetune(
        self: object,
        used_model: ModelRef,
        used_dataset: LearningDataset,
        used_config: TrainingConfig,
    ) -> TrainingResult:
        return _ok(used_model, used_config)

    monkeypatch.setattr(huggingface_mod.HuggingFaceBackend, "finetune", _finetune)
    report = replay_learning_experiment(record)
    assert isinstance(report, ReplayReport)
    assert report.comparison["identity_match"] is True
    assert report.record.experiment_id.endswith(".replay")


def test_scores_stay_in_unit_interval_under_random_payloads() -> None:
    rng = random.Random(7)
    for _ in range(100):
        payload = {
            "status": rng.choice(["ok", "FAILED", "VALIDATED", "nope"]),
            "units_ok": rng.choice([True, False, None]),
            "constraint_ok": rng.choice([True, False]),
            "tokens": rng.choice([None, 0.0, rng.random() * 50]),
            "latency": rng.choice([None, 0.0, rng.random() * 50]),
            "token_budget": rng.choice([None, 1.0, 25.0, 100.0]),
            "latency_budget": rng.choice([None, 1.0, 25.0, 100.0]),
        }
        clean = {key: value for key, value in payload.items() if value is not None}
        scores = execution_result_scores(clean)
        for value in scores.values():
            assert 0.0 <= value <= 1.0
