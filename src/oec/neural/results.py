"""Typed neural results — serialize into ExecutionResult.result (ADR 0031)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NeuralTrainingResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task: str
    backend: str = "torch"
    backend_version: str | None = None
    device: str
    seed: int
    deterministic_status: Literal["strict", "practical", "best_effort"]
    epochs_ran: int
    train_metrics: dict[str, float]
    val_metrics: dict[str, float] | None = None
    history: list[dict[str, float]] = Field(default_factory=list)
    # Compact checkpoint: state_dict as nested lists/floats for JSON skills
    checkpoint: dict[str, Any]
    normalize: dict[str, Any] | None = None
    model_spec: dict[str, Any]
    n_train: int
    n_val: int
    dataset_fingerprint: str
    model_fingerprint: str


class NeuralEvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task: str
    backend: str = "torch"
    backend_version: str | None = None
    device: str
    metrics: dict[str, float]
    n: int
    dataset_fingerprint: str
    predictions: list[float] | list[list[float]] | None = None
