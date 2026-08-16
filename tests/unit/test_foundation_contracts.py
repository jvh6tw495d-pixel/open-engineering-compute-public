"""W6 foundation contracts + builtin embed (no transformers required)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from oec.foundation.contracts import (
    EmbeddingBackend,
    EmbeddingSpec,
    FoundationModelSpec,
    GenerationSpec,
    PEFTMethod,
    PEFTSpec,
    TrainingBudgetSpec,
    TrainingDatasetSpec,
)
from oec.foundation.errors import (
    AdapterNotFoundError,
    BitsAndBytesNotAvailableError,
    FoundationError,
    PeftNotAvailableError,
    TransformersNotAvailableError,
)
from oec.foundation.runtime import (
    embed_texts,
    foundation_capabilities,
    generate_text,
    peft_train,
    probe_peft,
    probe_transformers,
)


def test_builtin_hash_embedding_reproducible() -> None:
    spec = EmbeddingSpec(
        backend=EmbeddingBackend.BUILTIN_HASH,
        texts=["alpha", "beta"],
        dim=16,
        seed=7,
        normalize=True,
    )
    a = embed_texts(spec)
    b = embed_texts(spec)
    assert a["vectors"] == b["vectors"]
    assert a["n"] == 2
    assert len(a["vectors"][0]) == 16
    assert a["merit_owner"] == "oec"


def test_capabilities_probe() -> None:
    caps = foundation_capabilities()
    assert "builtin_hash" in caps["embedding_backends"]
    assert "transformers_available" in caps


def test_transformers_backend_fail_closed_when_missing() -> None:
    avail, _, _ = probe_transformers()
    if avail:
        pytest.skip("transformers installed")
    with pytest.raises(TransformersNotAvailableError):
        embed_texts(
            EmbeddingSpec(
                backend=EmbeddingBackend.TRANSFORMERS,
                texts=["x"],
                dim=8,
            )
        )


# --- S1: PEFT / fine-tune contracts (ADR 0041) --------------------------------


def _model() -> FoundationModelSpec:
    return FoundationModelSpec(
        model_id="sshleifer/tiny-gpt2",
        revision="5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be",
    )


def test_peft_spec_schema_version_bumped() -> None:
    spec = PEFTSpec(model=_model(), dataset=TrainingDatasetSpec(texts=("hello",)))
    assert spec.schema_version == "0.2.0"
    assert spec.method == PEFTMethod.LORA
    assert spec.budget == TrainingBudgetSpec()


def test_training_dataset_requires_exactly_one_source() -> None:
    with pytest.raises(ValidationError):
        TrainingDatasetSpec()  # neither texts nor local_path
    with pytest.raises(ValidationError):
        TrainingDatasetSpec(texts=("a",), local_path="x.txt")  # both
    with pytest.raises(ValidationError):
        TrainingDatasetSpec(texts=())  # empty texts


def test_peft_spec_target_modules_allow_list() -> None:
    with pytest.raises(ValidationError):
        PEFTSpec(
            model=_model(),
            dataset=TrainingDatasetSpec(texts=("hello",)),
            target_modules=("arbitrary.python.path",),
        )
    with pytest.raises(ValidationError):
        PEFTSpec(
            model=_model(),
            dataset=TrainingDatasetSpec(texts=("hello",)),
            target_modules=(),
        )


def test_training_budget_hard_caps() -> None:
    with pytest.raises(ValidationError):
        TrainingBudgetSpec(max_steps=10_000)
    with pytest.raises(ValidationError):
        TrainingBudgetSpec(max_seq_len=100_000)
    with pytest.raises(ValidationError):
        TrainingBudgetSpec(batch_size=1_000)


def test_probe_peft() -> None:
    avail, _version, _reason = probe_peft()
    assert isinstance(avail, bool)
    caps = foundation_capabilities()
    assert "peft_available" in caps
    assert "training_methods" in caps


def test_peft_train_fail_closed_when_transformers_missing() -> None:
    avail, _, _ = probe_transformers()
    if avail:
        pytest.skip("transformers installed")
    spec = PEFTSpec(model=_model(), dataset=TrainingDatasetSpec(texts=("hello world",)))
    with pytest.raises(TransformersNotAvailableError):
        peft_train(spec)


def test_generate_with_missing_adapter_path_fails_closed() -> None:
    avail, _, _ = probe_transformers()
    if not avail:
        # transformers itself missing takes priority in generate_text's own probe.
        with pytest.raises(TransformersNotAvailableError):
            generate_text(GenerationSpec(prompt="hi", model=_model(), adapter_path="/no/such/dir"))
        return
    with pytest.raises(AdapterNotFoundError):
        generate_text(GenerationSpec(prompt="hi", model=_model(), adapter_path="/no/such/dir"))


def test_peft_qlora_without_bitsandbytes_or_peft_fails_closed() -> None:
    """Fail-closed for qlora: either transformers, peft, or bitsandbytes missing."""
    avail, _, _ = probe_transformers()
    if not avail:
        pytest.skip("covered by test_peft_train_fail_closed_when_transformers_missing")
    spec = PEFTSpec(
        method=PEFTMethod.QLORA,
        model=_model(),
        dataset=TrainingDatasetSpec(texts=("hello world",)),
    )
    with pytest.raises((PeftNotAvailableError, BitsAndBytesNotAvailableError, FoundationError)):
        peft_train(spec)


def test_peft_qlora_does_not_silently_train_full_precision_lora(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys
    from types import ModuleType

    import oec.foundation.runtime as runtime

    avail, _, _ = probe_transformers()
    if not avail:
        pytest.skip("transformers missing")
    try:
        import peft  # noqa: F401
    except ImportError:
        pytest.skip("peft missing")
    fake = ModuleType("bitsandbytes")
    monkeypatch.setitem(sys.modules, "bitsandbytes", fake)
    spec = PEFTSpec(
        method=PEFTMethod.QLORA,
        model=_model(),
        dataset=TrainingDatasetSpec(texts=("hello world",)),
    )
    with pytest.raises(FoundationError, match="4-bit"):
        runtime.peft_train(spec)
