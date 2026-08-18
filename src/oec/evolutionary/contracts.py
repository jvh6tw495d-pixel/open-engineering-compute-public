"""Declarative evolutionary problem/algorithm specs (no arbitrary callables)."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any, Literal

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

    Objective is either a ``built_in`` test function **or** a closed
    expression IR tree (Part B E-D2). Optional inequality constraints
    g(x) ≤ 0 via the same IR (E-D3).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    variables: list[VariableSpec]
    sense: Literal["min", "max"] = "min"
    # Default sphere when neither expression nor explicit built_in is the common path
    built_in: BuiltInProblemName | None = BuiltInProblemName.SPHERE
    # Closed operator IR (same allow-list as GP); vars must match VariableSpec names
    expression: dict[str, Any] | None = None
    # Inequality constraints: dicts with name+tree (g(x) <= 0) — validated at runtime
    constraints: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _vars(self) -> EvolutionaryProblemSpec:
        if not self.variables:
            raise ValueError("variables must be non-empty")
        names = [v.name for v in self.variables]
        if len(names) != len(set(names)):
            raise ValueError("variable names must be unique")
        if self.expression is None and self.built_in is None:
            raise ValueError("either built_in or expression is required")
        for i, c in enumerate(self.constraints):
            if not isinstance(c, dict) or "tree" not in c:
                raise ValueError(f"constraints[{i}] must be an object with a tree field")
            if "name" not in c:
                raise ValueError(f"constraints[{i}] must include name")
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


class NeatFitnessName(StrEnum):
    """Closed NEAT fitness catalog (ADR 0044). No caller Python."""

    XOR = "xor"
    TABULAR_REGRESSION = "tabular_regression"
    TABULAR_CLASSIFICATION = "tabular_classification"


class NeatProblemSpec(BaseModel):
    """NEAT problem: closed fitness + optional tabular arrays."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fitness: NeatFitnessName
    x: list[list[float]] | None = None
    y: list[float] | None = None

    @model_validator(mode="after")
    def _closed(self) -> NeatProblemSpec:
        if self.fitness == NeatFitnessName.XOR:
            if self.x is not None or self.y is not None:
                raise ValueError("xor fitness is closed; do not pass x/y")
            return self
        if self.x is None or self.y is None:
            raise ValueError(f"{self.fitness.value} requires x and y")
        if len(self.x) != len(self.y):
            raise ValueError("x and y must have the same length")
        if not self.x:
            raise ValueError("x must be non-empty")
        if len(self.x) > 2000:
            raise ValueError("x has at most 2000 rows")
        n_features = len(self.x[0])
        if n_features < 1 or n_features > 32:
            raise ValueError("each row of x must have 1–32 features")
        for row in self.x:
            if len(row) != n_features:
                raise ValueError("x must be rectangular")
            if any(not math.isfinite(v) for v in row):
                raise ValueError("x must be finite")
        if any(not math.isfinite(v) for v in self.y):
            raise ValueError("y must be finite")
        if self.fitness == NeatFitnessName.TABULAR_CLASSIFICATION:
            for value in self.y:
                if value < 0 or int(value) != value:
                    raise ValueError("classification y must be non-negative integers")
        return self


class NeatAlgorithmSpec(BaseModel):
    """Closed NEAT knobs (ADR 0044). Other neat-python keys stay at defaults."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    generations: int = Field(default=30, ge=1, le=500)
    population: int = Field(default=50, ge=4, le=500)
    seed: int = 42
    compatibility_threshold: float = Field(default=3.0, gt=0.0, le=20.0)
    compatibility_disjoint_coefficient: float = Field(default=1.0, ge=0.0, le=10.0)
    compatibility_weight_coefficient: float = Field(default=0.5, ge=0.0, le=10.0)
    conn_add_prob: float = Field(default=0.5, ge=0.0, le=1.0)
    conn_delete_prob: float = Field(default=0.5, ge=0.0, le=1.0)
    node_add_prob: float = Field(default=0.2, ge=0.0, le=1.0)
    node_delete_prob: float = Field(default=0.2, ge=0.0, le=1.0)
    num_hidden: int = Field(default=0, ge=0, le=16)
    elitism: int = Field(default=2, ge=0, le=20)
    feed_forward: bool = True
