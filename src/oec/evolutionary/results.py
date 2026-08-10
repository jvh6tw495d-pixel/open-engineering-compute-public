"""Typed evolutionary results — serialize into ExecutionResult.result."""

from __future__ import annotations

from typing import Any, Literal

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


class EvolutionaryParetoResult(BaseModel):
    """Non-dominated set from a multi-objective run (E2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: str = "pymoo"
    backend_version: str | None = None
    algorithm: str
    seed: int
    deterministic_status: Literal["strict", "practical", "best_effort"] = "practical"
    n_objectives: int
    # Parallel arrays / lists for JSON friendliness
    decision_vectors: list[dict[str, float]] = Field(default_factory=list)
    objective_vectors: list[list[float]] = Field(default_factory=list)
    nondominated_mask: list[bool] = Field(default_factory=list)
    n_nondominated: int = 0
    n_evaluations: int = 0
    n_generations: int = 0
    hypervolume: float | None = None
    problem_fingerprint: str
    message: str = "ok"


class BenchmarkResult(BaseModel):
    """X1 thin harness: controlled multi-algorithm / multi-seed table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["single", "multi"]
    backend: str = "pymoo"
    problem_fingerprint: str
    seeds: list[int]
    algorithms: list[str]
    # rows: {algorithm, seed, metric_name: value, n_evaluations, ...}
    rows: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    message: str = "ok"
