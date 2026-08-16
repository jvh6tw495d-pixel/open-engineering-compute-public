"""L6 (distillation) + L12 (worker pipeline) — real wiring, not stubs.

Every path either executes for real (when the relevant extra is installed and
the run has no network dependency) or fails closed with a structured error —
never a silent "planned"/dry-run stand-in for a real result.
"""

from __future__ import annotations

import builtins

import pytest

from oec.learning.contracts import FineTuneBackendName, ModelRef, TrainingMethod, TrainingResult
from oec.learning.datasets import DatasetKind, LearningDataset
from oec.learning.distillation import (
    DistillationConfig,
    DistillationResult,
    compare_base_vs_distilled,
    distill,
)
from oec.learning.errors import BackendNotAvailableError, LearningError
from oec.learning.pipeline import WorkerPipeline, WorkerStage, default_worker_dataset


def _tabular_dataset(n: int = 8) -> LearningDataset:
    return LearningDataset(
        name="distill-tabular",
        kind=DatasetKind.DISTILLATION,
        records=tuple({"x": [float(i)], "y": 2.0 * i + 1.0} for i in range(n)),
    )


def _text_only_dataset() -> LearningDataset:
    return LearningDataset(
        name="distill-sft-text",
        kind=DatasetKind.SFT,
        records=({"text": "solve x**2-2"}, {"text": "check units"}),
    )


def _block_import(name_to_block: str, monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def _blocked(name: str, *args: object, **kwargs: object) -> object:
        if name == name_to_block or name.startswith(f"{name_to_block}."):
            raise ImportError(f"simulated missing {name_to_block}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked)


# --------------------------------------------------------------------------
# L6 — distillation
# --------------------------------------------------------------------------


def test_distill_without_torch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _block_import("torch", monkeypatch)
    with pytest.raises(BackendNotAvailableError):
        distill(
            teacher=ModelRef(model_id="teacher/base"),
            student=ModelRef(model_id="student/small"),
            dataset=_tabular_dataset(),
        )


def test_distill_sft_text_only_dataset_fails_closed_with_learning_error() -> None:
    """SFT text records carry no tabular meaning — must fail, never stub."""
    pytest.importorskip("torch")
    with pytest.raises(LearningError):
        distill(
            teacher=ModelRef(model_id="teacher/base"),
            student=ModelRef(model_id="student/small"),
            dataset=_text_only_dataset(),
        )


def _cfg_from_teacher(*, alpha: float, seed: int) -> DistillationConfig:
    from oec.kernel.neural.training import train_mlp
    from oec.neural.contracts import DatasetSpec, NeuralModelSpec, TrainingSpec

    x = [[float(i)] for i in range(8)]
    y = [2.0 * i + 1.0 for i in range(8)]
    teacher = train_mlp(
        DatasetSpec(x=x, y=y, val_fraction=0.0),
        NeuralModelSpec(input_dim=1, hidden_dims=[8]),
        TrainingSpec(epochs=2, batch_size=8, seed=seed),
    )
    return DistillationConfig(
        alpha=alpha,
        seed=seed,
        max_epochs=2,
        teacher_checkpoint=teacher.checkpoint,
        teacher_normalize=teacher.normalize,
        student_hidden_dims=(4,),
    )


def test_distill_tabular_dataset_executes_real_training() -> None:
    pytest.importorskip("torch")
    result = distill(
        teacher=ModelRef(model_id="teacher/base"),
        student=ModelRef(model_id="student/small"),
        dataset=_tabular_dataset(),
        config=_cfg_from_teacher(alpha=0.5, seed=3),
    )
    assert isinstance(result, DistillationResult)
    assert result.status == "ok"
    assert "loss" in result.metrics
    assert isinstance(result.metrics["loss"], float)
    assert result.metrics["loss"] >= 0.0
    # Real numbers, not an invented/empty stub.
    assert result.metrics != {}


def test_distill_tabular_dataset_is_deterministic_for_fixed_seed() -> None:
    pytest.importorskip("torch")
    kwargs = dict(
        teacher=ModelRef(model_id="teacher/base"),
        student=ModelRef(model_id="student/small"),
        dataset=_tabular_dataset(),
        config=_cfg_from_teacher(alpha=0.5, seed=11),
    )
    first = distill(**kwargs)
    second = distill(**kwargs)
    assert first.metrics == second.metrics


def test_compare_base_vs_distilled_works_on_real_distillation_metrics() -> None:
    pytest.importorskip("torch")
    distilled = distill(
        teacher=ModelRef(model_id="teacher/base"),
        student=ModelRef(model_id="student/small"),
        dataset=_tabular_dataset(),
        config=_cfg_from_teacher(alpha=0.5, seed=5),
    )
    base = TrainingResult(
        status="ok",
        backend=FineTuneBackendName.HUGGINGFACE,
        method=TrainingMethod.SFT,
        model=ModelRef(model_id="teacher/base"),
        metrics={"loss": distilled.metrics["loss"] + 10.0},
    )
    report = compare_base_vs_distilled(base, distilled)
    assert report["comparisons"][0]["metric"] == "loss"
    assert report["comparisons"][0]["winner"] == "distilled"


# --------------------------------------------------------------------------
# L12 — worker pipeline
# --------------------------------------------------------------------------


def test_worker_pipeline_plan_is_a_dry_run_without_extras() -> None:
    pipe = WorkerPipeline(model=ModelRef(model_id="tiny"), dataset=default_worker_dataset())
    plan = pipe.plan()
    assert plan["stages"]
    assert plan["dataset_hash"] == pipe.dataset.content_hash


def test_worker_pipeline_run_fails_closed_for_unwired_backend() -> None:
    """A declared-but-unimplemented backend must fail closed, not silently plan."""
    pipe = WorkerPipeline(
        model=ModelRef(model_id="tiny"),
        dataset=default_worker_dataset(),
        stages=(WorkerStage(name="sft", method=TrainingMethod.SFT, backend="unsloth"),),
    )
    with pytest.raises(BackendNotAvailableError):
        pipe.run()


def test_worker_pipeline_run_fails_closed_for_unknown_backend_string() -> None:
    pipe = WorkerPipeline(
        model=ModelRef(model_id="tiny"),
        dataset=default_worker_dataset(),
        stages=(WorkerStage(name="sft", method=TrainingMethod.SFT, backend="totally-bogus"),),
    )
    with pytest.raises(BackendNotAvailableError):
        pipe.run()


def test_worker_pipeline_run_huggingface_stage_is_wired_or_fails_closed() -> None:
    """When oec[foundation] extras are missing, run() must fail closed (not plan)."""
    pipe = WorkerPipeline(
        model=ModelRef(model_id="sshleifer/tiny-gpt2"), dataset=default_worker_dataset()
    )
    try:
        import peft  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        with pytest.raises(BackendNotAvailableError):
            pipe.run()
    else:
        pytest.skip(
            "transformers/peft installed — network-dependent finetune not exercised "
            "in unit tests (consistent with existing L1-L5 huggingface backend tests)"
        )


def test_worker_pipeline_run_without_extras_does_not_return_silent_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even if transformers/peft are present, a blocked import must fail closed."""
    _block_import("transformers", monkeypatch)
    pipe = WorkerPipeline(model=ModelRef(model_id="tiny"), dataset=default_worker_dataset())
    with pytest.raises(BackendNotAvailableError):
        pipe.run()
