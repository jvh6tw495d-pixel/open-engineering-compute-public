"""Adversarial reproductions for Learning bugs found in the hunt."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from oec.common import VersionedRef
from oec.execution.models import ExecutionResult, ExecutionStatus
from oec.learning import (
    BackendNotAvailableError,
    FineTuneBackendName,
    LearningError,
    LearningRunRecord,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
    WorkerPipeline,
    default_worker_dataset,
)
from oec.learning.backends import huggingface as huggingface_mod
from oec.learning.backends.huggingface import HuggingFaceBackend
from oec.learning.contracts import ArtifactRef, ModelFamily
from oec.learning.pipeline import WorkerStage, payload_from_execution
from oec.learning.rl import Action, Episode, RLResult, State, Trajectory


def _execution(status: ExecutionStatus, *, duration_ms: float = 4.0) -> ExecutionResult:
    ref = VersionedRef(id="demo", version="0.1.0")
    now = datetime.now(UTC)
    return ExecutionResult(
        status=status,
        skill=ref,
        method=ref,
        started_at=now,
        completed_at=now,
        duration_ms=duration_ms,
        validation={"units_ok": True, "constraint_ok": True},
        diagnostics={"tokens": 2.0, "token_budget": 10.0},
    )


def test_art_only_pipeline_is_ok_not_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    import oec.learning.backends.art as art_module

    monkeypatch.setattr(
        art_module.importlib,
        "import_module",
        lambda _name: SimpleNamespace(
            train_grpo=lambda **_kwargs: RLResult(status="ok", backend="art")
        ),
    )
    pipe = WorkerPipeline(
        model=ModelRef(model_id="m"),
        dataset=default_worker_dataset(),
        stages=(WorkerStage(name="rl", method=TrainingMethod.SFT, backend="art"),),
        episodes=(
            Episode(
                episode_id="e",
                trajectory=Trajectory(
                    states=(State(), State(terminal=True)),
                    actions=(Action(name="a"),),
                    rewards=(1.0,),
                ),
            ),
        ),
    )
    out = pipe.run(experiment_id="art-only")
    assert out["status"] == "ok"
    assert out["rl"]


def test_converged_with_warnings_eval_is_acceptable() -> None:
    pipe = WorkerPipeline(
        model=ModelRef(model_id="m"),
        dataset=default_worker_dataset(),
        stages=(),
        evaluations=(_execution(ExecutionStatus.CONVERGED_WITH_WARNINGS),),
    )
    out = pipe.run()
    assert out["evaluation"]["status"] == "ok"
    assert out["status"] == "ok"


def test_failed_eval_hidden_by_later_success_is_failed() -> None:
    pipe = WorkerPipeline(
        model=ModelRef(model_id="m"),
        dataset=default_worker_dataset(),
        stages=(),
        evaluations=(
            _execution(ExecutionStatus.FAILED),
            _execution(ExecutionStatus.VERIFIED),
        ),
    )
    out = pipe.run()
    assert out["evaluation"]["status"] == "failed"
    assert out["status"] == "degraded"


def test_staged_failed_execution_is_not_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    def _finetune(
        self: object, model: ModelRef, dataset: object, config: TrainingConfig
    ) -> TrainingResult:
        return TrainingResult(
            status="ok",
            backend=config.backend,
            method=config.method,
            model=model,
            details={"execution": {"status": "FAILED", "units_ok": False}},
        )

    monkeypatch.setattr(huggingface_mod.HuggingFaceBackend, "finetune", _finetune)
    pipe = WorkerPipeline(
        model=ModelRef(model_id="tinyllama/tiny"),
        dataset=default_worker_dataset(),
        stages=(WorkerStage(name="one", method=TrainingMethod.LORA, backend="huggingface"),),
    )
    out = pipe.run()
    assert out["evaluation"]["status"] == "failed"


def test_record_rejects_revision_mismatch() -> None:
    dataset = default_worker_dataset()
    config = TrainingConfig(seed=dataset.seed)
    with pytest.raises(ValueError, match="revision"):
        LearningRunRecord(
            run_id="r",
            experiment_id="e",
            code_version={},
            environment={},
            hardware={},
            dataset=dataset,
            dataset_name=dataset.name,
            dataset_version=dataset.version,
            dataset_hash=dataset.content_hash,
            model_id="m",
            model_revision="aaa",
            model_family=ModelFamily.TRANSFORMERS,
            backend=FineTuneBackendName.HUGGINGFACE,
            config=config,
            seed=dataset.seed,
            result=TrainingResult(
                status="ok",
                backend=FineTuneBackendName.HUGGINGFACE,
                method=config.method,
                model=ModelRef(model_id="m", revision="bbb"),
            ),
        )


def test_huggingface_rejects_unpinned_adapter(tmp_path: Path) -> None:
    adapter = tmp_path / "prev"
    adapter.mkdir()
    with pytest.raises(BackendNotAvailableError, match="adapter_sha256"):
        HuggingFaceBackend().finetune(
            ModelRef(model_id="tinyllama/tiny"),
            default_worker_dataset(),
            TrainingConfig(
                method=TrainingMethod.LORA,
                hyperparameters={"adapter_path": str(adapter)},
            ),
        )


def test_pipeline_refuses_to_chain_adapter_without_sha256(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def _finetune(
        self: object, model: ModelRef, dataset: object, config: TrainingConfig
    ) -> TrainingResult:
        nonlocal calls
        calls += 1
        return TrainingResult(
            status="ok",
            backend=config.backend,
            method=config.method,
            model=model,
            artifact=ArtifactRef(path="/tmp/adapter", sha256=None),
        )

    monkeypatch.setattr(huggingface_mod.HuggingFaceBackend, "finetune", _finetune)
    pipe = WorkerPipeline(
        model=ModelRef(model_id="tinyllama/tiny"),
        dataset=default_worker_dataset(),
        stages=(
            WorkerStage(name="a", method=TrainingMethod.LORA, backend="huggingface"),
            WorkerStage(name="b", method=TrainingMethod.LORA, backend="huggingface"),
        ),
    )
    with pytest.raises(LearningError, match="sha256"):
        pipe.run()
    assert calls == 1


def test_payload_forwards_token_budget_from_diagnostics() -> None:
    payload = payload_from_execution(_execution(ExecutionStatus.VALIDATED))
    assert payload["tokens"] == 2.0
    assert payload["token_budget"] == 10.0
    assert payload["duration_ms"] == 4.0
