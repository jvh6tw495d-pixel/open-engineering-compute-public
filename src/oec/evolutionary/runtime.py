"""Evolutionary depth contracts (Part B / E-D0–E-D1).

Importable without pymoo. No free callables — expression IR only.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from oec.evolutionary.contracts import BudgetSpec


class InequalityConstraintSpec(BaseModel):
    """Inequality g(x) ≤ 0 via closed operator IR (same allow-list as GP)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    tree: dict[str, Any]


class EvolutionaryRuntimeSpec(BaseModel):
    """Shared runtime knobs for evolutionary runs (Part B.7)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int = 42
    seeds: list[int] | None = None
    budget: BudgetSpec | None = None
    max_seconds: float | None = Field(default=None, gt=0.0)
    max_evaluations: int | None = Field(default=None, ge=1)
    history: bool = True
    hv_reference: list[float] | None = None

    def resolved_seeds(self) -> list[int]:
        if self.seeds is not None and len(self.seeds) > 0:
            return list(self.seeds)
        return [self.seed]

    @model_validator(mode="after")
    def _hv_ref(self) -> EvolutionaryRuntimeSpec:
        if self.hv_reference is not None and len(self.hv_reference) < 2:
            raise ValueError("hv_reference must have at least 2 components for bi-objective")
        return self


class MultiSeedReport(BaseModel):
    """E-D4 multi-seed aggregate for a single algorithm/problem."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: str
    seeds: list[int]
    best_objectives: list[float]
    mean_best_objective: float
    std_best_objective: float
    min_best_objective: float
    max_best_objective: float
    mean_n_evaluations: float
    rows: list[dict[str, Any]] = Field(default_factory=list)
    problem_fingerprint: str
    message: str = "ok"
