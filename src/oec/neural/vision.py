"""Vision transfer contracts — backbone is a backend, the head is OEC.

Core-safe: no torch / torchvision import.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VisionBackboneName(StrEnum):
    """Closed catalog. Weights stay in the backend (torchvision / HF)."""

    RESNET18 = "resnet18"
    CLIP = "clip"


class VisionTransferMode(StrEnum):
    """How the application uses the backbone."""

    FROZEN_FEATURES = "frozen_features"  # extract once, train an OEC MLP
    FINETUNE_HEAD = "finetune_head"  # freeze backbone, train a new head on pixels
    FINETUNE_LAST = "finetune_last"  # unfreeze last block + head


class VisionBackboneWeights(StrEnum):
    IMAGENET = "imagenet"
    NONE = "none"


class VisionLabeledImage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(min_length=1)
    label: int = Field(ge=0)


class VisionTransferSpec(BaseModel):
    """One governed vision-transfer run (dataset local, backbone explicit)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["0.1.0"] = "0.1.0"
    examples: tuple[VisionLabeledImage, ...] = Field(min_length=2)
    n_classes: int = Field(ge=2)
    backbone: VisionBackboneName = VisionBackboneName.RESNET18
    mode: VisionTransferMode = VisionTransferMode.FROZEN_FEATURES
    backbone_weights: VisionBackboneWeights = VisionBackboneWeights.IMAGENET
    # CLIP remote models need a 40-hex revision (fail-closed).
    clip_model_id: str = "openai/clip-vit-base-patch32"
    clip_revision: str | None = None
    hidden_dims: tuple[int, ...] = (64, 64)
    epochs: int = Field(default=20, ge=1, le=500)
    batch_size: int = Field(default=8, ge=1, le=64)
    lr: float = Field(default=1e-3, gt=0.0)
    val_fraction: float = Field(default=0.25, ge=0.0, lt=1.0)
    seed: int = 0
    device: Literal["cpu", "cuda", "auto"] = "cpu"

    @model_validator(mode="after")
    def _labels_in_range(self) -> VisionTransferSpec:
        bad = [ex.label for ex in self.examples if ex.label >= self.n_classes]
        if bad:
            raise ValueError(f"labels must be in 0..{self.n_classes - 1}")
        if self.backbone is VisionBackboneName.CLIP and not self.clip_revision:
            raise ValueError("clip_revision (40-hex) is required for backbone=clip")
        return self
