"""Scientific IR v0 — Math IR + species + laws + properties (v2.9).

Extends the domain-agnostic Math IR (ADR 0020) with **references** to
chemistry species, physics/chemistry laws, and material properties. The
document is declarative JSON-serialisable; it does not execute solvers.
Execution remains in domain owners (``oec.physics``, ``oec.chemistry``,
``oec.kernel``).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from oec.modeling.ir import IR_SCHEMA_VERSION, Symbol

SCIENTIFIC_IR_SCHEMA_VERSION = "0.1.0"


class SpeciesDecl(BaseModel):
    """Species declared in a Scientific IR document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    formula: dict[str, int]
    charge: int = 0
    phase: str | None = None

    @field_validator("formula")
    @classmethod
    def _formula(cls, value: dict[str, int]) -> dict[str, int]:
        if not value:
            raise ValueError("species formula must be non-empty")
        for el, n in value.items():
            if n <= 0:
                raise ValueError(f"atom count for {el!r} must be positive")
        return value


class LawRef(BaseModel):
    """Reference to an executable law id owned by physics/chemistry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["law"] = "law"
    id: str = Field(min_length=1)
    domain: str = Field(min_length=1)  # e.g. physics.thermal, chemistry.kinetics
    version: str | None = None


class PropertyRef(BaseModel):
    """Reference to a material / thermophysical property id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["property"] = "property"
    id: str = Field(min_length=1)
    source: str | None = None  # e.g. materials table id


class ReactionDecl(BaseModel):
    """Stoichiometric reaction declaration (nu map)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    nu: dict[str, float]

    @field_validator("nu")
    @classmethod
    def _nu(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("reaction nu must be non-empty")
        return {k: float(v) for k, v in value.items()}


class ConservationGoal(BaseModel):
    """Declare a conservation residual that solvers must close."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    quantity: str = Field(min_length=1)  # mass, energy, charge, mole, ...
    unit: str = Field(min_length=1)
    atol: float = Field(ge=0.0, default=1e-9)
    rtol: float = Field(ge=0.0, default=0.0)


class ScientificDocument(BaseModel):
    """Versioned Scientific IR document (v0).

    Combines Math IR symbols with species, reactions, law/property refs,
    and optional conservation goals. Problem payload is an open dict so
    existing Math IR problem kinds can be embedded without forking.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = SCIENTIFIC_IR_SCHEMA_VERSION
    math_ir_schema_version: str = IR_SCHEMA_VERSION
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    symbols: tuple[Symbol, ...] = ()
    species: tuple[SpeciesDecl, ...] = ()
    reactions: tuple[ReactionDecl, ...] = ()
    laws: tuple[LawRef, ...] = ()
    properties: tuple[PropertyRef, ...] = ()
    conservation: tuple[ConservationGoal, ...] = ()
    problem: dict[str, Any] = Field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    references: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _reaction_species_exist(self) -> ScientificDocument:
        known = {s.id for s in self.species}
        for rxn in self.reactions:
            missing = set(rxn.nu) - known
            if missing and known:
                raise ValueError(
                    f"reaction {rxn.id!r} references undeclared species: {sorted(missing)}"
                )
        return self

    def to_manifest(self) -> dict[str, Any]:
        """JSON-ready dict (Pydantic dump)."""
        return self.model_dump(mode="json")

    @classmethod
    def from_manifest(cls, data: dict[str, Any]) -> ScientificDocument:
        return cls.model_validate(data)


# Type alias for open extension points
ScientificNode = Annotated[
    LawRef | PropertyRef,
    Field(discriminator="kind"),
]


__all__ = [
    "SCIENTIFIC_IR_SCHEMA_VERSION",
    "ConservationGoal",
    "LawRef",
    "PropertyRef",
    "ReactionDecl",
    "ScientificDocument",
    "ScientificNode",
    "SpeciesDecl",
]
