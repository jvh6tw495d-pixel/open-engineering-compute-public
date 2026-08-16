"""L2 persist / L3 replay / L6 tabular / L12 run / L13 probe closeout."""

from __future__ import annotations

import pytest

from oec.learning import (
    BackendNotAvailableError,
    FineTuneBackendName,
    LearningDataset,
    ModelRef,
    TrainingConfig,
    TrainingResult,
    WorkerPipeline,
    default_worker_dataset,
    distill,
    execution_result_reward,
    execution_result_scores,
    measure_capability_suite,
)
from oec.learning.backends import huggingface as huggingface_mod
from oec.learning.backends.unsloth import UnslothBackend
from oec.learning.datasets import DatasetKind
from oec.learning.distillation import DistillationConfig, DistillationResult
from oec.learning.environments import RewardSpec


def _ok_result(model: ModelRef, config: TrainingConfig) -> TrainingResult:
    return TrainingResult(
        status="ok",
        backend=config.backend,
        method=config.method,
        model=model,
        metrics={"loss": 0.25},
        message="stub",
    )


def test_worker_pipeline_run_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _missing(
        self: object, model: ModelRef, dataset: LearningDataset, config: TrainingConfig
    ) -> TrainingResult:
        raise BackendNotAvailableError("huggingface extra missing")

    monkeypatch.setattr(huggingface_mod.HuggingFaceBackend, "finetune", _missing)
    pipe = WorkerPipeline(model=ModelRef(model_id="tiny"), dataset=default_worker_dataset())
    with pytest.raises(BackendNotAvailableError):
        pipe.run(experiment_id="w.e2e")


def test_worker_pipeline_run_executes_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    def _finetune(
        self: object, model: ModelRef, dataset: LearningDataset, config: TrainingConfig
    ) -> TrainingResult:
        return _ok_result(model, config)

    monkeypatch.setattr(huggingface_mod.HuggingFaceBackend, "finetune", _finetune)
    pipe = WorkerPipeline(model=ModelRef(model_id="tiny"), dataset=default_worker_dataset())
    out = pipe.run(experiment_id="w.e2e")
    assert out["status"] == "ok"
    assert len(out["records"]) == 2
    assert out["records"][0]["experiment_id"] == "w.e2e.sft"
    assert out["records"][1]["experiment_id"] == "w.e2e.peft"


def test_unsloth_hf_fallback_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    fake = types.ModuleType("unsloth")

    class FastLanguageModel:
        @staticmethod
        def from_pretrained(*_args: object, **_kwargs: object) -> tuple[object, object]:
            raise RuntimeError("unsloth API mismatch")

    fake.FastLanguageModel = FastLanguageModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "unsloth", fake)

    ds = LearningDataset(name="x", kind=DatasetKind.SFT, records=({"text": "a"}, {"text": "b"}))
    model = ModelRef(model_id="m")
    backend = UnslothBackend()
    with pytest.raises(BackendNotAvailableError, match="adapter not wired"):
        backend.finetune(model, ds, TrainingConfig(backend=FineTuneBackendName.UNSLOTH))

    def _finetune(
        self: object,
        used_model: ModelRef,
        used_dataset: LearningDataset,
        used_config: TrainingConfig,
    ) -> TrainingResult:
        return TrainingResult(
            status="ok",
            backend=FineTuneBackendName.HUGGINGFACE,
            method=used_config.method,
            model=used_model,
            metrics={"loss": 0.25},
            message="huggingface fallback",
        )

    monkeypatch.setattr(huggingface_mod.HuggingFaceBackend, "finetune", _finetune)
    result = backend.finetune(
        model,
        ds,
        TrainingConfig(
            backend=FineTuneBackendName.UNSLOTH,
            hyperparameters={"allow_hf_fallback": "1"},
        ),
    )
    assert result.status == "ok"
    assert result.backend is FineTuneBackendName.HUGGINGFACE


def test_execution_result_verifier_aliases() -> None:
    spec = RewardSpec(correct=2.0, units=0.5, constraints=1.0)
    payload = {"status": "VALIDATED", "units_ok": True, "constraints_ok": True}
    scores = execution_result_scores(payload)
    assert scores["correct"] == 1.0
    assert execution_result_reward(payload, spec) == pytest.approx(3.5)


def test_measure_capability_suite_does_not_invent_gpu_metrics() -> None:
    report = measure_capability_suite()
    assert report["benchmark"] == "learning-capability-probe"
    assert "loss" not in report
    assert "vram_gb" not in report
    assert "L5" in report["wired"]
    assert "L14" in report["wired"]


def test_distill_tabular_runs_when_torch_present() -> None:
    try:
        import torch  # noqa: F401
    except ImportError:
        pytest.skip("torch not installed — tabular distill path not exercised")
    dataset = LearningDataset(
        name="tab-distill",
        kind=DatasetKind.DISTILLATION,
        records=tuple({"x": [float(i)], "y": 2.0 * i + 1.0} for i in range(8)),
    )
    result = distill(
        teacher=ModelRef(model_id="teacher"),
        student=ModelRef(model_id="student"),
        dataset=dataset,
        config=DistillationConfig(temperature=2.0, alpha=0.5, seed=1, max_epochs=2),
    )
    assert isinstance(result, DistillationResult)
    assert result.status == "ok"
    assert result.metrics
    assert result.details["path"] == "neural.distill_mlp"
