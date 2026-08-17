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


def test_target_metric_equal_distance_is_a_tie() -> None:
    from oec.learning.contracts import MetricDirection, MetricSpec
    from oec.learning.evaluation import Benchmark, compare_results

    out = compare_results(
        Benchmark(
            name="t",
            metrics=(MetricSpec(name="x", direction=MetricDirection.TARGET, target=0.0),),
        ),
        {"x": 1.0},
        {"x": 1.0},
    )
    assert out["comparisons"][0]["winner"] == "tie"


def test_constant_target_wrong_prediction_is_not_perfect_r2() -> None:
    import numpy as np

    from oec.kernel.neural.metrics import regression_metrics

    perfect = regression_metrics(np.array([5.0, 5.0, 5.0]), np.array([5.0, 5.0, 5.0]))
    wrong = regression_metrics(np.array([5.0, 5.0, 5.0]), np.array([0.0, 0.0, 0.0]))
    assert perfect["r_squared"] == pytest.approx(1.0)
    assert wrong["r_squared"] == pytest.approx(0.0)


def test_generate_refuses_unpinned_adapter(tmp_path: Path) -> None:
    from oec.foundation.contracts import FoundationModelSpec, GenerationSpec
    from oec.foundation.errors import FoundationError
    from oec.foundation.runtime import generate_text, probe_transformers

    avail, _, _ = probe_transformers()
    if not avail:
        pytest.skip("transformers missing")
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "dummy.txt").write_text("x", encoding="utf-8")
    with pytest.raises(FoundationError, match="adapter_sha256"):
        generate_text(
            GenerationSpec(
                prompt="hi",
                model=FoundationModelSpec(
                    model_id="sshleifer/tiny-gpt2",
                    revision="5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be",
                ),
                adapter_path=str(adapter),
            )
        )


def test_experiment_record_hash_matches_bytes_on_disk(tmp_path: Path) -> None:
    import hashlib

    from oec.experiment.artifacts import persist_experiment_record
    from oec.experiment.record import ExperimentRecord, ExperimentStatus
    from oec.experiment.specs import ExperimentSpec, ExperimentStep

    spec = ExperimentSpec(
        id="hash-check",
        steps=(ExperimentStep(step_id="noop", skill_id="mathematics.identity", inputs={"x": 1}),),
    )
    record = ExperimentRecord(status=ExperimentStatus.COMPLETED, spec=spec, seed=0)
    final, produced = persist_experiment_record(record, artifact_root=tmp_path)
    rec_art = next(item for item in produced if item.name == "record")
    raw = Path(rec_art.path).read_bytes()
    assert rec_art.content_hash == hashlib.sha256(raw).hexdigest()
    disk = __import__("json").loads(raw)
    assert all(item.get("name") != "record" for item in disk.get("artifacts_produced", []))


def test_peft_builder_rejects_full_checkpoint_reload() -> None:
    from oec.experiment.cross_domain import build_peft_train_then_generate_experiment

    with pytest.raises(ValueError, match="full"):
        build_peft_train_then_generate_experiment(mode="full")


def test_payload_forwards_token_budget_from_diagnostics() -> None:
    payload = payload_from_execution(_execution(ExecutionStatus.VALIDATED))
    assert payload["tokens"] == 2.0
    assert payload["token_budget"] == 10.0
    assert payload["duration_ms"] == 4.0
