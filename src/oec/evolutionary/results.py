"""Typed evolutionary results — serialize into ExecutionResult.result."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    # Part B depth metadata
    n_constraints: int = 0
    objective_mode: Literal["built_in", "expression"] = "built_in"
    runtime: dict[str, Any] | None = None


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
    hv_reference: list[float] | None = None
    problem_fingerprint: str
    message: str = "ok"
    runtime: dict[str, Any] | None = None


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


class NeatNodeIR(BaseModel):
    """OEC-owned NEAT node (ADR 0044)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    kind: Literal["input", "hidden", "output"]
    bias: float | None = None
    response: float | None = None
    activation: str | None = None
    aggregation: str | None = None


class NeatConnectionIR(BaseModel):
    """OEC-owned NEAT connection (ADR 0044)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: int
    target: int
    weight: float
    enabled: bool
    innovation: int | None = None


class NeatGenotypeIR(BaseModel):
    """Serializable genotype. Never a neat-python genome object."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nodes: tuple[NeatNodeIR, ...]
    connections: tuple[NeatConnectionIR, ...]
    n_inputs: int
    n_outputs: int
    feed_forward: bool = True
    fitness: float | None = None
    key: int | None = None


class NeatResult(BaseModel):
    """NEAT run payload serialized into ExecutionResult.result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: str = "neat-python"
    backend_version: str | None = None
    algorithm: str = "neat"
    seed: int
    deterministic_status: Literal["strict", "practical", "best_effort"] = "practical"
    fitness: str
    sense: Literal["max"] = "max"
    best_fitness: float
    genotype: NeatGenotypeIR
    n_nodes: int
    n_connections: int
    n_enabled_connections: int
    n_species: int = 0
    n_evaluations: int = 0
    n_generations: int = 0
    history_best: list[float] = Field(default_factory=list)
    problem_fingerprint: str
    message: str = "ok"
    runtime: dict[str, Any] | None = None


class HyperNeatSubstrateNodeIR(BaseModel):
    """One neuron on a fixed HyperNEAT substrate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    kind: Literal["input", "hidden", "output"]
    x: float
    y: float


class HyperNeatSubstrateIR(BaseModel):
    """OEC-owned substrate after CPPN expression (ADR 0045 / 0048)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    kind: Literal["layered_1d", "es_hyperneat"]
    extraction: Literal["cartesian", "gauci_quadtree"]
    nodes: tuple[HyperNeatSubstrateNodeIR, ...]
    connections: tuple[NeatConnectionIR, ...]
    n_inputs: int
    n_outputs: int
    hidden_layers: int | None = None
    hidden_width: int | None = None
    actual_hidden: int = 0
    weight_threshold: float
    max_depth: int | None = None
    variance_threshold: float | None = None
    band_threshold: float | None = None
    max_iteration: int | None = None
    n_iterations_used: int | None = None

    @model_validator(mode="after")
    def _kind_matches_fields(self) -> HyperNeatSubstrateIR:
        if self.kind == "es_hyperneat":
            if self.extraction != "gauci_quadtree":
                raise ValueError("es_hyperneat extraction must be gauci_quadtree")
            if self.hidden_layers is not None or self.hidden_width is not None:
                raise ValueError("es_hyperneat must not set hidden_layers/hidden_width")
            if self.max_depth is None or self.band_threshold is None:
                raise ValueError("es_hyperneat requires max_depth and band_threshold")
            return self
        if self.extraction != "cartesian":
            raise ValueError("layered_1d extraction must be cartesian")
        if self.hidden_layers is None or self.hidden_width is None:
            raise ValueError("layered_1d requires hidden_layers and hidden_width")
        return self


class HyperNeatResult(BaseModel):
    """HyperNEAT run: CPPN genotype + expressed substrate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: str = "neat-python"
    backend_version: str | None = None
    algorithm: str = "hyperneat"
    seed: int
    deterministic_status: Literal["strict", "practical", "best_effort"] = "practical"
    fitness: str
    sense: Literal["max"] = "max"
    best_fitness: float
    cppn: NeatGenotypeIR
    substrate: HyperNeatSubstrateIR
    n_cppn_nodes: int
    n_substrate_connections: int
    n_species: int = 0
    n_evaluations: int = 0
    n_generations: int = 0
    history_best: list[float] = Field(default_factory=list)
    problem_fingerprint: str
    message: str = "ok"
    runtime: dict[str, Any] | None = None
