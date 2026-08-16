"""Live, deliberately tiny learning smoke tests for optional runtimes."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_TINY_GPT2 = "sshleifer/tiny-gpt2"
_TINY_GPT2_REVISION = "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be"


def _require_modules(*names: str) -> None:
    missing = [name for name in names if importlib.util.find_spec(name) is None]
    if missing:
        pytest.skip("optional learning dependencies missing: " + ", ".join(missing))


def _is_network_or_cache_error(exc: BaseException) -> bool:
    """Recognize the offline/cache failures that make a live HF smoke inapplicable."""
    message = str(exc).lower()
    markers = (
        "couldn't connect",
        "could not connect",
        "connection error",
        "network is unreachable",
        "offline mode",
        "not found in the cached files",
        "not a local folder and is not a valid model identifier",
        "local cache",
        "cache directory",
        "failed to resolve",
    )
    return any(marker in message for marker in markers)


@pytest.mark.foundation
@pytest.mark.learning_smoke
def test_huggingface_lora_can_continue_from_saved_adapter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _require_modules("transformers", "peft", "torch")

    from oec.learning.backends.huggingface import HuggingFaceBackend
    from oec.learning.contracts import ModelRef, TrainingConfig, TrainingMethod
    from oec.learning.datasets import DatasetKind, LearningDataset

    monkeypatch.setenv("OEC_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    model = ModelRef(model_id=_TINY_GPT2, revision=_TINY_GPT2_REVISION)
    dataset = LearningDataset(
        name="tiny-gpt2-sft-smoke",
        kind=DatasetKind.SFT,
        records=(
            {"text": "The answer is small."},
            {"text": "Adapters preserve the base model."},
        ),
    )
    config = TrainingConfig(
        method=TrainingMethod.LORA,
        max_steps=1,
        max_seq_len=32,
        batch_size=1,
    )
    backend = HuggingFaceBackend()

    try:
        stage1 = backend.finetune(model, dataset, config)
    except Exception as exc:
        if _is_network_or_cache_error(exc):
            pytest.skip(f"tiny GPT-2 unavailable from network/cache: {exc}")
        raise

    assert stage1.artifact is not None
    assert stage1.artifact.path or stage1.artifact.sha256
    assert stage1.artifact.path is not None

    continued_config = config.model_copy(
        update={"hyperparameters": {"adapter_path": stage1.artifact.path}}
    )
    try:
        stage2 = backend.finetune(model, dataset, continued_config)
    except Exception as exc:
        if _is_network_or_cache_error(exc):
            pytest.skip(f"tiny GPT-2 unavailable from network/cache: {exc}")
        raise

    assert stage2.details.get("continued_from_adapter") is True or (
        stage2.details.get("base_adapter_path") == stage1.artifact.path
    )


@pytest.mark.neural
@pytest.mark.learning_smoke
def test_tabular_distillation_uses_real_teacher_checkpoint() -> None:
    _require_modules("torch")

    from oec.kernel.neural.training import train_mlp
    from oec.learning.contracts import ModelRef
    from oec.learning.datasets import DatasetKind, LearningDataset
    from oec.learning.distillation import DistillationConfig, distill
    from oec.neural.contracts import DatasetSpec, NeuralModelSpec, TrainingSpec

    x = [[float(i)] for i in range(4)]
    y = [2.0 * value[0] + 1.0 for value in x]
    teacher = train_mlp(
        DatasetSpec(x=x, y=y, val_fraction=0.0),
        NeuralModelSpec(input_dim=1, hidden_dims=[4]),
        TrainingSpec(epochs=1, batch_size=4, seed=1),
    )
    result = distill(
        teacher=ModelRef(model_id="smoke-teacher"),
        student=ModelRef(model_id="smoke-student"),
        dataset=LearningDataset(
            name="tabular-distillation-smoke",
            kind=DatasetKind.DISTILLATION,
            records=tuple({"x": row, "y": target} for row, target in zip(x, y, strict=True)),
        ),
        config=DistillationConfig(
            max_epochs=1,
            teacher_checkpoint=teacher.checkpoint,
            teacher_normalize=teacher.normalize,
            student_hidden_dims=(4,),
        ),
    )

    assert result.status == "ok"
    assert result.metrics
