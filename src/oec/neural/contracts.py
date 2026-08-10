"""Declarative neural specs — closed enums only (no arbitrary Python)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NeuralTask(StrEnum):
    REGRESSION = "regression"
    BINARY_CLASSIFICATION = "binary_classification"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"


class ActivationName(StrEnum):
    RELU = "relu"
    GELU = "gelu"
    TANH = "tanh"
    SIGMOID = "sigmoid"
    IDENTITY = "identity"


class LossName(StrEnum):
    MSE = "mse"
    MAE = "mae"
    HUBER = "huber"
    BCE = "bce"
    CROSS_ENTROPY = "cross_entropy"


class OptimizerName(StrEnum):
    ADAM = "adam"
    ADAMW = "adamw"
    SGD = "sgd"


class DeviceSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    device: Literal["cpu", "cuda", "auto"] = "cpu"


class DatasetSpec(BaseModel):
    """Tabular arrays only — no external downloads in N0/N1."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # 2D features [n, d]
    x: list[list[float]]
    # regression: list[float]; classification: list[int] as float-compatible
    y: list[float]
    val_fraction: float = Field(default=0.2, ge=0.0, lt=1.0)

    @field_validator("x")
    @classmethod
    def _x_nonempty(cls, value: list[list[float]]) -> list[list[float]]:
        if len(value) < 2:
            raise ValueError("dataset x must have at least 2 rows")
        width = len(value[0])
        if width < 1:
            raise ValueError("dataset x must have at least 1 feature")
        if any(len(row) != width for row in value):
            raise ValueError("dataset x rows must share the same width")
        return value

    @field_validator("y")
    @classmethod
    def _y_nonempty(cls, value: list[float]) -> list[float]:
        if len(value) < 2:
            raise ValueError("dataset y must have at least 2 values")
        return value


class NeuralModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    architecture: Literal["mlp"] = "mlp"
    input_dim: int = Field(ge=1)
    output_dim: int = Field(default=1, ge=1)
    hidden_dims: list[int] = Field(default_factory=lambda: [64, 32])
    activation: ActivationName = ActivationName.RELU
    dropout: float = Field(default=0.0, ge=0.0, lt=1.0)

    @field_validator("hidden_dims")
    @classmethod
    def _hidden_positive(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("hidden_dims must be non-empty")
        if any(h < 1 for h in value):
            raise ValueError("hidden_dims entries must be >= 1")
        return value


class OptimizerSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: OptimizerName = OptimizerName.ADAM
    lr: float = Field(default=1e-3, gt=0.0)
    weight_decay: float = Field(default=0.0, ge=0.0)


class TrainingSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task: NeuralTask = NeuralTask.REGRESSION
    epochs: int = Field(default=50, ge=1, le=10_000)
    batch_size: int = Field(default=32, ge=1)
    loss: LossName = LossName.MSE
    optimizer: OptimizerSpec = Field(default_factory=OptimizerSpec)
    early_stopping_patience: int | None = Field(default=10, ge=1)
    seed: int = Field(default=42)
    device: DeviceSpec = Field(default_factory=DeviceSpec)
    normalize_x: bool = True
