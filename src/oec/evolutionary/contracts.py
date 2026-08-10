"""Declarative evolutionary problem/algorithm specs (no arbitrary callables)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlgorithmName(StrEnum):
    DIFFERENTIAL_EVOLUTION = "differential_evolution"
    GENETIC_ALGORITHM = "genetic_algorithm"
    CMA_ES = "cma_es"
    PSO = "pso"


class BuiltInProblemName(StrEnum):
    """Safe built-in test problems for E1.0 (no user Python)."""

    SPHERE = "sphere"
    ROSENBROCK = "rosenbrock"
    RASTRIGIN = "rastrigin"


class VariableSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    lower: float
    upper: float

    @model_validator(mode="after")
    def _bounds(self) -> VariableSpec:
        if self.upper <= self.lower:
            raise ValueError(f"variable {self.name!r}: upper must be > lower")
        return self


class BudgetSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    generations: int = Field(default=50, ge=1, le=10_000)
    population: int = Field(default=40, ge=4, le=5_000)


class EvolutionaryProblemSpec(BaseModel):
    """Single-objective box-constrained problem.

    E1.0: ``built_in`` test functions only. Expression IR is a later slice.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    variables: list[VariableSpec]
    sense: Literal["min", "max"] = "min"
    built_in: BuiltInProblemName = BuiltInProblemName.SPHERE

    @model_validator(mode="after")
    def _vars(self) -> EvolutionaryProblemSpec:
        if not self.variables:
            raise ValueError("variables must be non-empty")
        names = [v.name for v in self.variables]
        if len(names) != len(set(names)):
            raise ValueError("variable names must be unique")
        return self


class EvolutionaryAlgorithmSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: AlgorithmName = AlgorithmName.DIFFERENTIAL_EVOLUTION
    budget: BudgetSpec = Field(default_factory=BudgetSpec)
    seed: int = 42
