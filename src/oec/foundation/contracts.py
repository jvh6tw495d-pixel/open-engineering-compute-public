"""Closed foundation-model specs (W6 + S1 PEFT/FT) — no arbitrary Python from agents."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EmbeddingBackend(StrEnum):
    """Embedding backends. ``builtin_hash`` is OEC-owned (not an LLM)."""

    BUILTIN_HASH = "builtin_hash"
    TRANSFORMERS = "transformers"


class GenerationBackend(StrEnum):
    TRANSFORMERS = "transformers"


class PEFTMethod(StrEnum):
    """Training mode (ADR 0041): ``lora``/``qlora`` wrap a PEFT adapter,

    ``none`` trains all base-model parameters (full fine-tune).
    """

    LORA = "lora"
    QLORA = "qlora"
    NONE = "none"


class ArtifactKind(StrEnum):
    ADAPTER = "adapter"
    CHECKPOINT = "checkpoint"


# ADR 0041 S1: closed allow-list for LoRA target module names. Agents cannot
# supply arbitrary attribute paths into the base model.
ALLOWED_TARGET_MODULES: frozenset[str] = frozenset(
    {
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
        "c_attn",
        "c_proj",
        "c_fc",
        "query",
        "key",
        "value",
        "dense",
    }
)


class FoundationModelSpec(BaseModel):
    """Reference to a foundation model (id only — no auto-download in core)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    model_id: str = Field(min_length=1, description="HF hub id or local path label")
    revision: str | None = None
    trust_remote_code: bool = False  # always false in W6 skills


class EmbeddingSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    backend: EmbeddingBackend = EmbeddingBackend.BUILTIN_HASH
    texts: list[str] = Field(min_length=1)
    dim: int = Field(default=32, ge=8, le=1024)
    model: FoundationModelSpec | None = None
    normalize: bool = True
    seed: int = 0


class GenerationSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    backend: GenerationBackend = GenerationBackend.TRANSFORMERS
    prompt: str = Field(min_length=1)
    max_new_tokens: int = Field(default=32, ge=1, le=512)
    model: FoundationModelSpec = Field(
        default_factory=lambda: FoundationModelSpec(model_id="sshleifer/tiny-gpt2")
    )
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: int = 0
    # S1 (ADR 0041 §3.2): optional adapter/checkpoint reload. A path that is
    # missing or unloadable fails closed — never a silent base-model swap.
    adapter_path: str | None = Field(default=None, min_length=1)


class TrainingDatasetSpec(BaseModel):
    """Inline texts or a local path label — never a silent hub download."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    texts: tuple[str, ...] | None = None
    local_path: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _check_exactly_one_source(self) -> TrainingDatasetSpec:
        has_texts = self.texts is not None
        has_path = self.local_path is not None
        if has_texts == has_path:
            raise ValueError("dataset requires exactly one of texts or local_path")
        if has_texts and len(self.texts) == 0:  # type: ignore[arg-type]
            raise ValueError("texts must be non-empty when provided")
        return self


class TrainingBudgetSpec(BaseModel):
    """Hard caps on training cost (ADR 0041 §1) so a request cannot runaway."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    max_steps: int = Field(default=20, ge=1, le=500)
    max_seq_len: int = Field(default=64, ge=8, le=1024)
    batch_size: int = Field(default=2, ge=1, le=32)


class PEFTSpec(BaseModel):
    """PEFT / full fine-tune training plan (ADR 0041 S1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.2.0"] = "0.2.0"
    method: PEFTMethod = PEFTMethod.LORA
    model: FoundationModelSpec
    dataset: TrainingDatasetSpec
    budget: TrainingBudgetSpec = Field(default_factory=TrainingBudgetSpec)
    r: int = Field(default=8, ge=1, le=256)
    lora_alpha: int = Field(default=16, ge=1)
    lora_dropout: float = Field(default=0.05, ge=0.0, lt=1.0)
    target_modules: tuple[str, ...] = ("q_proj", "v_proj")
    seed: int = 0

    @field_validator("target_modules")
    @classmethod
    def _check_target_modules(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("target_modules must be non-empty")
        unknown = sorted(set(value) - ALLOWED_TARGET_MODULES)
        if unknown:
            raise ValueError(
                f"target_modules not in allow-list {sorted(ALLOWED_TARGET_MODULES)}: {unknown}"
            )
        return value


class TrainingArtifact(BaseModel):
    """Machine-readable descriptor for a trained adapter/checkpoint (ADR 0041 §3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    kind: ArtifactKind
    path: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    base_model_id: str = Field(min_length=1)
    revision: str | None = None
