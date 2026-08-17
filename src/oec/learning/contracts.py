"""Closed Learning contracts (L1) — no external ML types."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from oec.learning.datasets import LearningDataset

from pydantic import BaseModel, ConfigDict, Field

LEARNING_SCHEMA_VERSION: Literal["0.1.0"] = "0.1.0"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = LEARNING_SCHEMA_VERSION


class ModelFamily(StrEnum):
    PYTORCH = "pytorch"
    TRANSFORMERS = "transformers"
    SCIENTIFIC = "scientific"
    EXTERNAL_REF = "external_ref"


class TrainingMethod(StrEnum):
    SUPERVISED = "supervised"
    SFT = "sft"
    LORA = "lora"
    QLORA = "qlora"
    FULL = "full"
    DISTILL = "distill"


class FineTuneBackendName(StrEnum):
    HUGGINGFACE = "huggingface"
    UNSLOTH = "unsloth"
    AXOLOTL = "axolotl"


class MetricDirection(StrEnum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    TARGET = "target"


class ModelRef(_Frozen):
    """Public model identity — never a live HF/torch object."""

    model_id: str = Field(min_length=1)
    family: ModelFamily = ModelFamily.TRANSFORMERS
    revision: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class TrainingConfig(_Frozen):
    method: TrainingMethod = TrainingMethod.LORA
    backend: FineTuneBackendName = FineTuneBackendName.HUGGINGFACE
    seed: int = 0
    max_steps: int = Field(default=8, ge=1, le=500)
    max_seq_len: int = Field(default=64, ge=8, le=1024)
    batch_size: int = Field(default=1, ge=1, le=32)
    hyperparameters: dict[str, float | int | str] = Field(default_factory=dict)


class ArtifactRef(_Frozen):
    kind: str = "checkpoint"
    path: str | None = None
    sha256: str | None = None
    base_model_id: str | None = None
    revision: str | None = None


class TrainingResult(_Frozen):
    status: str
    backend: FineTuneBackendName
    method: TrainingMethod
    model: ModelRef
    artifact: ArtifactRef | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class MetricSpec(_Frozen):
    name: str = Field(min_length=1)
    direction: MetricDirection = MetricDirection.MINIMIZE
    target: float | None = None


@runtime_checkable
class FineTuneBackend(Protocol):
    """Replaceable training backend (L5+). Implementations must not leak HF types."""

    name: FineTuneBackendName

    def finetune(
        self,
        model: ModelRef,
        dataset: LearningDataset,
        config: TrainingConfig,
    ) -> TrainingResult: ...
