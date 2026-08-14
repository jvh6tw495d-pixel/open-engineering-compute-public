"""Closed foundation-model specs (W6 + S1 PEFT/FT) — no arbitrary Python from agents."""

from __future__ import annotations

import re
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
        default_factory=lambda: FoundationModelSpec(
            model_id="sshleifer/tiny-gpt2",
            revision="5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be",
        )
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


# ---------------------------------------------------------------------------
# S5 VLM MVP (ADR 0040 D3) — closed vision / VLM contracts
# ---------------------------------------------------------------------------

ALLOWED_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp"})
MAX_IMAGE_BYTES: int = 5 * 1024 * 1024  # compressed source bytes
# Bounds are applied from decoded image metadata before ``load()`` / ``convert()``.
MAX_IMAGE_PIXELS: int = 16_000_000
MAX_IMAGE_DIMENSION: int = 8_192
MAX_IMAGE_FRAMES: int = 1
_HF_COMMIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class VisionBackend(StrEnum):
    """Only Transformers is in-scope for the S5 VLM MVP."""

    TRANSFORMERS = "transformers"


def is_local_model_path(model_id: str) -> bool:
    """True when ``model_id`` names an existing local path (local-only mode)."""
    from pathlib import Path

    p = Path(model_id)
    return p.exists()


def require_pinned_or_local_model(model: FoundationModelSpec) -> None:
    """Fail closed: remote HF labels need an immutable revision; no remote code.

    Local directory/file model ids are the explicit local-only escape hatch.
    """
    if model.trust_remote_code:
        raise ValueError("trust_remote_code must be false (unsafe remote code disabled)")
    if is_local_model_path(model.model_id):
        return
    revision = str(model.revision or "").strip()
    if not revision:
        raise ValueError(
            "revision is required for remote Hugging Face model ids "
            "(fail-closed reproducibility; use a local path for local-only mode)"
        )
    if not _HF_COMMIT_SHA_RE.fullmatch(revision):
        raise ValueError(
            "revision for remote Hugging Face model ids must be an immutable 40-hex commit SHA"
        )


class VisionImageInput(BaseModel):
    """Bounded raster input — base64 bytes or a controlled local path.

    No URL download. Extension and decoded-size bounds are enforced at runtime
    load; schema rejects obvious URL schemes and disallowed path suffixes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    image_base64: str | None = Field(default=None, min_length=1)
    image_path: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _exactly_one_source(self) -> VisionImageInput:
        has_b64 = self.image_base64 is not None
        has_path = self.image_path is not None
        if has_b64 == has_path:
            raise ValueError("image requires exactly one of image_base64 or image_path")
        if has_path:
            path = str(self.image_path)
            lower = path.strip().lower()
            if lower.startswith("http://") or lower.startswith("https://"):
                raise ValueError("image_path must be a local path; URL download is not allowed")
            from pathlib import Path

            suffix = Path(path).suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTENSIONS:
                raise ValueError(
                    f"image_path extension must be one of {sorted(ALLOWED_IMAGE_EXTENSIONS)}"
                )
        return self


class VisionEmbeddingSpec(BaseModel):
    """Governed vision embedding request (S5 MVP)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    backend: VisionBackend = VisionBackend.TRANSFORMERS
    images: list[VisionImageInput] = Field(min_length=1)
    model: FoundationModelSpec
    dim: int = Field(default=512, ge=8, le=4096)
    normalize: bool = True
    seed: int = 0

    @model_validator(mode="after")
    def _check_model_pin(self) -> VisionEmbeddingSpec:
        require_pinned_or_local_model(self.model)
        return self


class VLMGenerationSpec(BaseModel):
    """Governed vision-language generation request (S5 MVP)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    backend: VisionBackend = VisionBackend.TRANSFORMERS
    prompt: str = Field(min_length=1)
    image: VisionImageInput
    model: FoundationModelSpec
    max_new_tokens: int = Field(default=32, ge=1, le=512)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: int = 0

    @model_validator(mode="after")
    def _check_model_pin(self) -> VLMGenerationSpec:
        require_pinned_or_local_model(self.model)
        return self
