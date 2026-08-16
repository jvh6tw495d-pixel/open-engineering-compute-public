"""Learning L6–L15 — core-safe contracts and fail-closed adapters."""

from __future__ import annotations

import pytest

from oec.learning import (
    BackendNotAvailableError,
    FineTuneBackendName,
    LearningDataset,
    LearningError,
    MathematicsEnvironment,
    ModelRef,
    RewardSpec,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
    WorkerPipeline,
    capability_matrix,
    compare_backend_runs,
    compare_base_vs_distilled,
    declared_backends,
    default_worker_dataset,
    distill,
    probe_optional,
    select_backend,
)
from oec.learning.backends.art import ARTBackend
from oec.learning.backends.axolotl import AxolotlBackend, recipe_to_experiment
from oec.learning.distillation import DistillationConfig
from oec.learning.rl import Action, Episode, State, Trajectory


def test_distill_fail_closed_without_torch_or_without_torch_texts() -> None:
    """default_worker_dataset() is SFT text-only — always fails closed under distill()."""
    ds = default_worker_dataset()
    teacher = ModelRef(model_id="teacher")
    student = ModelRef(model_id="student")
    try:
        import torch  # noqa: F401
    except ImportError:
        with pytest.raises(BackendNotAvailableError):
            distill(teacher=teacher, student=student, dataset=ds, config=DistillationConfig())
    else:
        with pytest.raises(LearningError):
            distill(teacher=teacher, student=student, dataset=ds)


def test_compare_base_vs_distilled() -> None:
    base = TrainingResult(
        status="ok",
        backend=FineTuneBackendName.HUGGINGFACE,
        method=TrainingMethod.LORA,
        model=ModelRef(model_id="s"),
        metrics={"loss": 1.0},
    )
    distilled = TrainingResult(
        status="ok",
        backend=FineTuneBackendName.HUGGINGFACE,
        method=TrainingMethod.DISTILL,
        model=ModelRef(model_id="s"),
        metrics={"loss": 0.4},
    )
    report = compare_base_vs_distilled(base, distilled)
    assert report["comparisons"][0]["winner"] == "distilled"


def test_unsloth_and_axolotl_fail_closed() -> None:
    ds = LearningDataset(name="x", records=({"text": "a"}, {"text": "b"}))
    model = ModelRef(model_id="m")
    cfg = TrainingConfig(backend=FineTuneBackendName.UNSLOTH)
    with pytest.raises(BackendNotAvailableError):
        select_backend(FineTuneBackendName.UNSLOTH).finetune(model, ds, cfg)
    with pytest.raises(BackendNotAvailableError):
        AxolotlBackend().finetune(model, ds, TrainingConfig(backend=FineTuneBackendName.AXOLOTL))


def test_axolotl_recipe_is_oec_experiment() -> None:
    exp = recipe_to_experiment(
        {"base_model": "tiny", "texts": ["hi"], "seed": 1}, experiment_id="ax.1"
    )
    assert exp.config.backend is FineTuneBackendName.AXOLOTL
    assert exp.dataset.content_hash


def test_art_fail_closed() -> None:
    env = MathematicsEnvironment()
    traj = Trajectory(states=(State(),), actions=(), rewards=())
    episode = Episode(episode_id="e1", trajectory=traj)
    with pytest.raises(BackendNotAvailableError):
        ARTBackend().train(env, (episode,))


def test_scientific_reward_is_deterministic() -> None:
    spec = RewardSpec(correct=1.0, units=0.5, tokens=0.1, latency=0.0, constraints=0.0)
    scores = {
        "correct": 1.0,
        "units": 1.0,
        "constraints": 0.0,
        "tokens": 2.0,
        "latency": 0.0,
    }
    value = spec.reward(scores)
    assert value == pytest.approx(1.0 + 0.5 + 0.2)
    assert MathematicsEnvironment().name == "mathematics"
    _ = Action


def test_worker_pipeline_plan() -> None:
    pipe = WorkerPipeline(model=ModelRef(model_id="tiny"), dataset=default_worker_dataset())
    plan = pipe.plan()
    assert plan["stages"]
    exp = pipe.as_experiment(experiment_id="w.demo")
    assert exp.experiment_id == "w.demo"


def test_backend_suite_and_capability_matrix() -> None:
    report = compare_backend_runs(
        {"loss": 1.0, "vram_gb": 8.0, "train_seconds": 10.0},
        {"loss": 0.9, "vram_gb": 6.0, "train_seconds": 8.0},
    )
    assert report["benchmark"] == "learning-backend-suite"
    names = declared_backends()
    assert "huggingface" in names["finetune"]
    assert "art" in names["rl"]
    matrix = capability_matrix()
    assert {row["wave"] for row in matrix} >= {"L5", "L7", "L10", "L12", "L14"}
    assert "torch" in probe_optional()
