"""Species declarations and ideal mixture composition (v2.8 C1).

Concentrations and mole fractions are pure numbers with explicit unit
strings on the quantity side; this module does not re-implement unit
conversion (ADR 0016 / 0025 remain owned by kernel.units / physics.units).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from oec.chemistry.errors import ChemistryEvaluationError


class Species(BaseModel):
    """A chemical species with an elemental formula map.

    ``formula`` maps element symbol → atom count, e.g. ``{"H": 2, "O": 1}``
    for water. Charge (ionic species) is optional and tracked separately.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    formula: dict[str, int]
    charge: int = 0
    phase: str | None = None  # e.g. "g", "l", "s", "aq"

    @field_validator("formula")
    @classmethod
    def _validate_formula(cls, value: dict[str, int]) -> dict[str, int]:
        if not value:
            raise ValueError("species formula must declare at least one element")
        cleaned: dict[str, int] = {}
        for element, count in value.items():
            if not element or not element[0].isalpha():
                raise ValueError(f"invalid element symbol {element!r}")
            if count <= 0:
                raise ValueError(f"atom count for {element!r} must be positive")
            cleaned[element] = int(count)
        return cleaned


class Composition(BaseModel):
    """Molar amounts (mol) for a set of species ids."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    amounts_mol: dict[str, float]

    @field_validator("amounts_mol")
    @classmethod
    def _finite_nonneg(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("composition requires at least one species")
        out: dict[str, float] = {}
        for sid, n in value.items():
            if not sid:
                raise ValueError("species id must be non-empty")
            n_f = float(n)
            if n_f < 0.0 or n_f != n_f:  # NaN check
                raise ValueError(f"amount for {sid!r} must be finite and >= 0")
            if n_f == float("inf"):
                raise ValueError(f"amount for {sid!r} must be finite")
            out[sid] = n_f
        return out

    @property
    def total_mol(self) -> float:
        return sum(self.amounts_mol.values())

    def mole_fraction(self, species_id: str) -> float:
        total = self.total_mol
        if total <= 0.0:
            raise ChemistryEvaluationError(
                "mole fraction undefined for zero total amount",
                details={"species_id": species_id},
            )
        if species_id not in self.amounts_mol:
            raise ChemistryEvaluationError(
                f"species {species_id!r} not in composition",
                details={"species_id": species_id},
            )
        return self.amounts_mol[species_id] / total

    def concentrations_mol_per_m3(self, volume_m3: float) -> dict[str, float]:
        """Return c_i = n_i / V for each species (mol/m³)."""
        v = float(volume_m3)
        if v <= 0.0 or v != v or v == float("inf"):
            raise ChemistryEvaluationError(
                "volume_m3 must be finite and positive",
                details={"volume_m3": volume_m3},
            )
        return {sid: n / v for sid, n in self.amounts_mol.items()}


class Mixture(BaseModel):
    """Species catalogue + composition at one state point."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    species: dict[str, Species]
    composition: Composition

    @model_validator(mode="after")
    def _composition_subset(self) -> Mixture:
        unknown = set(self.composition.amounts_mol) - set(self.species)
        if unknown:
            raise ValueError(f"composition references unknown species: {sorted(unknown)}")
        return self


__all__ = ["Composition", "Mixture", "Species"]
