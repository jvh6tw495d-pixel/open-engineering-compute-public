"""L2 persist / L3 replay / L6 tabular / L12 run / L13 probe closeout."""

from __future__ import annotations

from datetime import UTC

import pytest

from oec.learning import (
    BackendNotAvailableError,
    FineTuneBackendName,
    LearningDataset,
    LearningError,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
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
    datasets_mod = types.ModuleType("datasets")

    class Dataset:
        @staticmethod
        def from_list(rows: object) -> object:
            return rows

    datasets_mod.Dataset = Dataset  # type: ignore[attr-defined]
    transformers_mod = types.ModuleType("transformers")
    transformers_mod.TrainingArguments = lambda **_kwargs: object()  # type: ignore[attr-defined]
    trl_mod = types.ModuleType("trl")
    trl_mod.SFTTrainer = object  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "datasets", datasets_mod)
    monkeypatch.setitem(sys.modules, "transformers", transformers_mod)
    monkeypatch.setitem(sys.modules, "trl", trl_mod)

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


def test_reward_tokens_and_latency_are_monotonic_efficiency() -> None:
    spec = RewardSpec(correct=0.0, units=0.0, constraints=0.0, tokens=1.0, latency=1.0)
    cheap = {
        "status": "ok",
        "tokens": 10.0,
        "token_budget": 100.0,
        "latency": 5.0,
        "latency_budget": 20.0,
    }
    expensive = {
        "status": "ok",
        "tokens": 80.0,
        "token_budget": 100.0,
        "latency": 18.0,
        "latency_budget": 20.0,
    }
    assert execution_result_reward(cheap, spec) > execution_result_reward(expensive, spec)
    no_budget = {"status": "ok", "tokens": 50.0, "latency": 10.0}
    missing = {"status": "ok"}
    measured_zero = {"status": "ok", "tokens": 0.0, "latency": 0.0}
    assert execution_result_scores(missing)["tokens"] == 0.0
    assert execution_result_scores(measured_zero)["tokens"] == 1.0
    assert execution_result_scores(no_budget)["tokens"] == 0.0


def test_sft_prompt_completion_keeps_both_fields() -> None:
    from oec.learning.datasets import texts_from_sft

    dataset = LearningDataset(
        name="sft-pairs",
        kind=DatasetKind.SFT,
        records=({"prompt": "Q?", "completion": "A."},),
    )
    assert texts_from_sft(dataset) == ["Q?\nA."]


def test_worker_evaluate_uses_execution_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import datetime

    from oec.common import VersionedRef
    from oec.execution.models import ExecutionResult, ExecutionStatus

    def _finetune(
        self: object, model: ModelRef, dataset: LearningDataset, config: TrainingConfig
    ) -> TrainingResult:
        return _ok_result(model, config)

    monkeypatch.setattr(huggingface_mod.HuggingFaceBackend, "finetune", _finetune)
    execution = ExecutionResult(
        status=ExecutionStatus.VALIDATED,
        skill=VersionedRef(id="physics.demo", version="1.0.0"),
        method=VersionedRef(id="method.demo", version="1.0.0"),
        validation={"units_ok": True, "constraints_ok": True},
        diagnostics={"tokens": 0},
        duration_ms=12.0,
        started_at=datetime.now(UTC),
    )
    pipe = WorkerPipeline(
        model=ModelRef(model_id="tinyllama/tiny"),
        dataset=default_worker_dataset(),
        evaluations=(execution,),
    )
    out = pipe.run(experiment_id="w.eval")
    assert out["evaluation"]["status"] == "ok"
    assert out["evaluation"]["source"] == "execution_result"
    assert out["evaluation"]["scores"]["correct"] == 1.0


def test_art_stage_without_episodes_fails_closed() -> None:
    from oec.learning.pipeline import WorkerStage

    pipe = WorkerPipeline(
        model=ModelRef(model_id="tiny"),
        dataset=default_worker_dataset(),
        stages=(WorkerStage(name="rl", method=TrainingMethod.SFT, backend="art"),),
    )
    with pytest.raises(LearningError, match="episodes"):
        pipe.run(experiment_id="w.art")


def test_axolotl_materializes_jsonl_not_inline_list() -> None:
    from oec.learning.backends.axolotl import _materialize_jsonl

    path = _materialize_jsonl(default_worker_dataset())
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0]
        assert "solve x**2-2" in first
        assert path.suffix == ".jsonl"
    finally:
        path.unlink(missing_ok=True)


def test_huggingface_unknown_family_requires_target_modules() -> None:
    from oec.learning.backends.huggingface import HuggingFaceBackend

    backend = HuggingFaceBackend()
    with pytest.raises(BackendNotAvailableError, match="target_modules"):
        backend.finetune(
            ModelRef(model_id="some-org/mystery-model"),
            default_worker_dataset(),
            TrainingConfig(method=TrainingMethod.LORA),
        )


def test_huggingface_forwards_adapter_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from oec.learning.backends import huggingface as hf_mod

    captured: dict[str, object] = {}

    def _fake_peft_train(spec: object, **_kwargs: object) -> dict[str, object]:
        captured["adapter_path"] = getattr(spec, "adapter_path", None)
        return {
            "status": "ok",
            "final_loss": 0.1,
            "artifact": {"kind": "adapter", "path": "/tmp/out", "sha256": "a" * 64},
        }

    import oec.foundation.runtime as foundation_runtime

    monkeypatch.setattr(foundation_runtime, "peft_train", _fake_peft_train)
    result = hf_mod.HuggingFaceBackend().finetune(
        ModelRef(model_id="tinyllama/tiny"),
        default_worker_dataset(),
        TrainingConfig(
            method=TrainingMethod.LORA,
            hyperparameters={"adapter_path": "/tmp/prev-adapter"},
        ),
    )
    assert captured["adapter_path"] == "/tmp/prev-adapter"
    assert result.details["continued_from_adapter"] is True


def test_huggingface_sft_requires_explicit_lora_mapping() -> None:
    from oec.learning.backends.huggingface import HuggingFaceBackend

    backend = HuggingFaceBackend()
    with pytest.raises(BackendNotAvailableError, match="sft_via_lora"):
        backend.finetune(
            ModelRef(model_id="m"),
            default_worker_dataset(),
            TrainingConfig(method=TrainingMethod.SFT),
        )


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
    from oec.kernel.neural.training import train_mlp
    from oec.neural.contracts import DatasetSpec, NeuralModelSpec, TrainingSpec

    teacher = train_mlp(
        DatasetSpec(
            x=[[float(i)] for i in range(8)],
            y=[2.0 * i + 1.0 for i in range(8)],
            val_fraction=0.0,
        ),
        NeuralModelSpec(input_dim=1, hidden_dims=[8]),
        TrainingSpec(epochs=2, batch_size=8, seed=1),
    )
    result = distill(
        teacher=ModelRef(model_id="teacher"),
        student=ModelRef(model_id="student"),
        dataset=dataset,
        config=DistillationConfig(
            temperature=2.0,
            alpha=0.5,
            seed=1,
            max_epochs=2,
            teacher_checkpoint=teacher.checkpoint,
            teacher_normalize=teacher.normalize,
            student_hidden_dims=(4,),
        ),
    )
    assert isinstance(result, DistillationResult)
    assert result.status == "ok"
    assert result.metrics
    assert result.details["path"] == "neural.distill_mlp"
