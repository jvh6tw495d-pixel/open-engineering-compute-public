"""Typed evolutionary results — serialize into ExecutionResult.result."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvolutionaryResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: str = "pymoo"
    backend_version: str | None = None
    algorithm: str
    seed: int
    deterministic_status: Literal["strict", "practical", "best_effort"] = "practical"
    sense: Literal["min", "max"]
    best_objective: float
    best_x: dict[str, float]
    n_evaluations: int
    n_generations: int
    history_best: list[float] = Field(default_factory=list)
    problem_fingerprint: str
    feasibility_rate: float = 1.0
    message: str = ""
