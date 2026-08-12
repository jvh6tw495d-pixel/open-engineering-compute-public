"""Closed foundation-model specs (W6) — no arbitrary Python from agents."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingBackend(StrEnum):
    """Embedding backends. ``builtin_hash`` is OEC-owned (not an LLM)."""

    BUILTIN_HASH = "builtin_hash"
    TRANSFORMERS = "transformers"


class GenerationBackend(StrEnum):
    TRANSFORMERS = "transformers"


class PEFTMethod(StrEnum):
    """Parameter-efficient fine-tuning methods (contract freeze; runtime later)."""

    LORA = "lora"
    QLORA = "qlora"
    NONE = "none"


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


class PEFTSpec(BaseModel):
    """Fine-tuning / PEFT plan (schema freeze for W6; full train loop is future)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    method: PEFTMethod = PEFTMethod.LORA
    model: FoundationModelSpec
    r: int = Field(default=8, ge=1, le=256)
    lora_alpha: int = Field(default=16, ge=1)
    lora_dropout: float = Field(default=0.05, ge=0.0, lt=1.0)
    target_modules: tuple[str, ...] = ("q_proj", "v_proj")
