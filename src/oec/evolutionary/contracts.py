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


class MultiObjectiveAlgorithmName(StrEnum):
    """Population multi-objective algorithms (E2, pymoo)."""

    NSGA2 = "nsga2"
    NSGA3 = "nsga3"
    MOEAD = "moead"


class BuiltInProblemName(StrEnum):
    """Safe built-in test problems for E1.0 (no user Python)."""

    SPHERE = "sphere"
    ROSENBROCK = "rosenbrock"
    RASTRIGIN = "rastrigin"


class BuiltInMultiProblemName(StrEnum):
    """Safe bi-objective built-ins for E2 (no user Python)."""

    ZDT1 = "zdt1"
    ZDT2 = "zdt2"
    # f1=sum x^2, f2=sum (x-1)^2 — separable bi-sphere
    BI_SPHERE = "bi_sphere"


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


class MultiObjectiveProblemSpec(BaseModel):
    """Box-constrained multi-objective problem (E2 built-ins only)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variables: list[VariableSpec]
    built_in: BuiltInMultiProblemName = BuiltInMultiProblemName.ZDT1
    # All objectives minimized in built-ins (pymoo convention).
    n_objectives: int = Field(default=2, ge=2, le=3)

    @model_validator(mode="after")
    def _vars(self) -> MultiObjectiveProblemSpec:
        if not self.variables:
            raise ValueError("variables must be non-empty")
        names = [v.name for v in self.variables]
        if len(names) != len(set(names)):
            raise ValueError("variable names must be unique")
        bi_obj = {
            BuiltInMultiProblemName.ZDT1,
            BuiltInMultiProblemName.ZDT2,
            BuiltInMultiProblemName.BI_SPHERE,
        }
        if self.built_in in bi_obj and self.n_objectives != 2:
            raise ValueError(f"{self.built_in} requires n_objectives=2")
        return self


class MultiObjectiveAlgorithmSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: MultiObjectiveAlgorithmName = MultiObjectiveAlgorithmName.NSGA2
    budget: BudgetSpec = Field(default_factory=BudgetSpec)
    seed: int = 42
    # NSGA-III reference directions (ignored by NSGA-II)
    n_partitions: int = Field(default=12, ge=1, le=50)


class BenchmarkSpec(BaseModel):
    """X1 thin: same problem, multiple algorithms and seeds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["single", "multi"] = "single"
    # Single-objective fields
    built_in: BuiltInProblemName | None = None
    algorithms: list[AlgorithmName] = Field(default_factory=list)
    # Multi-objective fields
    multi_built_in: BuiltInMultiProblemName | None = None
    multi_algorithms: list[MultiObjectiveAlgorithmName] = Field(default_factory=list)
    variables: list[VariableSpec]
    generations: int = Field(default=20, ge=1, le=500)
    population: int = Field(default=20, ge=4, le=500)
    seeds: list[int] = Field(default_factory=lambda: [0, 1, 2])

    @model_validator(mode="after")
    def _consistent(self) -> BenchmarkSpec:
        if not self.variables:
            raise ValueError("variables must be non-empty")
        if not self.seeds:
            raise ValueError("seeds must be non-empty")
        if self.mode == "single":
            if self.built_in is None:
                raise ValueError("built_in required for mode=single")
            if not self.algorithms:
                raise ValueError("algorithms required for mode=single")
        else:
            if self.multi_built_in is None:
                raise ValueError("multi_built_in required for mode=multi")
            if not self.multi_algorithms:
                raise ValueError("multi_algorithms required for mode=multi")
        return self
