"""L6–L8 Learning layer — distillation + Unsloth/Axolotl backends (fail-closed)."""

from __future__ import annotations

import subprocess
import sys

import pytest
from pydantic import ValidationError

from oec.learning.backends.axolotl import AxolotlBackend, recipe_to_experiment
from oec.learning.backends.unsloth import UnslothBackend
from oec.learning.contracts import (
    FineTuneBackendName,
    ModelRef,
    TrainingConfig,
    TrainingMethod,
    TrainingResult,
)
from oec.learning.datasets import DatasetKind, LearningDataset
from oec.learning.distillation import (
    DistillationConfig,
    DistillationResult,
    compare_base_vs_distilled,
    distill,
)
from oec.learning.errors import BackendNotAvailableError
from oec.learning.experiments import LearningExperiment


def test_import_l6_l8_does_not_load_backend_libraries() -> None:
    code = (
        "import sys; "
        "import oec.learning.distillation; "
        "import oec.learning.backends.unsloth; "
        "import oec.learning.backends.axolotl; "
        "print(','.join(sorted(name for name in sys.modules "
        "if name.split('.', 1)[0] in {'unsloth', 'axolotl'})))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )
    assert completed.stdout.strip() == ""


def _tiny_dataset() -> LearningDataset:
    return LearningDataset(
        name="distill-tiny",
        kind=DatasetKind.DISTILLATION,
        records=({"text": "alpha"}, {"text": "beta"}),
    )


def test_distillation_config_defaults_and_validation() -> None:
    cfg = DistillationConfig()
    assert cfg.temperature == 2.0
    assert cfg.alpha == 0.5
    with pytest.raises(ValidationError):
        DistillationConfig(temperature=0.0)
    with pytest.raises(ValidationError):
        DistillationConfig(alpha=1.5)


def test_distill_without_torch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch" or name.startswith("torch."):
            raise ImportError("simulated missing torch")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    with pytest.raises(BackendNotAvailableError):
        distill(
            teacher=ModelRef(model_id="teacher/base"),
            student=ModelRef(model_id="student/small"),
            dataset=_tiny_dataset(),
        )


def test_distill_with_torch_returns_planned_result_without_invented_metrics() -> None:
    try:
        import torch  # noqa: F401
    except ImportError:
        pytest.skip("torch not installed — planned-result path not exercised")
    result = distill(
        teacher=ModelRef(model_id="teacher/base"),
        student=ModelRef(model_id="student/small"),
        dataset=_tiny_dataset(),
        config=DistillationConfig(temperature=3.0, alpha=0.25, seed=7),
    )
    assert isinstance(result, DistillationResult)
    assert result.status == "planned"
    assert result.metrics == {}
    assert "temperature=3.0" in result.message
    assert "alpha=0.25" in result.message


def test_compare_base_vs_distilled_picks_lower_loss() -> None:
    base = TrainingResult(
        status="ok",
        backend=FineTuneBackendName.HUGGINGFACE,
        method=TrainingMethod.SFT,
        model=ModelRef(model_id="teacher/base"),
        metrics={"loss": 1.0},
    )
    distilled = TrainingResult(
        status="ok",
        backend=FineTuneBackendName.HUGGINGFACE,
        method=TrainingMethod.DISTILL,
        model=ModelRef(model_id="student/small"),
        metrics={"loss": 0.6},
    )
    out = compare_base_vs_distilled(base, distilled)
    assert out["comparisons"][0]["winner"] == "distilled"


def test_unsloth_backend_fail_closed_without_package() -> None:
    backend = UnslothBackend()
    assert backend.name == FineTuneBackendName.UNSLOTH
    with pytest.raises(BackendNotAvailableError):
        backend.finetune(
            ModelRef(model_id="local/demo"),
            _tiny_dataset(),
            TrainingConfig(backend=FineTuneBackendName.UNSLOTH),
        )


def test_axolotl_backend_fail_closed_without_package() -> None:
    backend = AxolotlBackend()
    assert backend.name == FineTuneBackendName.AXOLOTL
    with pytest.raises(BackendNotAvailableError):
        backend.finetune(
            ModelRef(model_id="local/demo"),
            _tiny_dataset(),
            TrainingConfig(backend=FineTuneBackendName.AXOLOTL),
        )


def test_recipe_to_experiment_translates_declarative_recipe() -> None:
    recipe = {
        "base_model": "meta/llama-tiny",
        "name": "axolotl-smoke",
        "datasets": [{"text": "hello"}, {"text": "world"}],
        "seed": 3,
    }
    exp = recipe_to_experiment(recipe, experiment_id="learn.l8.smoke")
    assert isinstance(exp, LearningExperiment)
    assert exp.experiment_id == "learn.l8.smoke"
    assert exp.model.model_id == "meta/llama-tiny"
    assert exp.dataset.name == "axolotl-smoke"
    assert exp.dataset.kind == DatasetKind.SFT
    assert len(exp.dataset.records) == 2
    assert exp.config.backend == FineTuneBackendName.AXOLOTL
    assert exp.config.seed == 3


def test_recipe_to_experiment_defaults_when_sparse() -> None:
    exp = recipe_to_experiment({}, experiment_id="learn.l8.sparse")
    assert exp.model.model_id == "unknown"
    assert len(exp.dataset.records) == 1
    assert exp.config.seed == 0
