"""Reaction stoichiometry and molar extent (v2.8 C1).

A reaction is declared by stoichiometric coefficients (reactants negative,
products positive). Atom and charge balance are enforced at construction.
"""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from oec.chemistry.errors import StoichiometryError
from oec.chemistry.species import Composition, Species
from oec.physics.conservation import evaluate_residual
from oec.physics.result import ConservationCheck


class Reaction(BaseModel):
    """Stoichiometric reaction over a closed species set.

    ``nu`` maps species_id → signed coefficient (negative = reactant).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    nu: dict[str, float]
    species: dict[str, Species]

    @field_validator("nu")
    @classmethod
    def _nu_nonempty(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("reaction requires at least one stoichiometric coefficient")
        cleaned: dict[str, float] = {}
        for sid, coeff in value.items():
            c = float(coeff)
            if c == 0.0 or c != c or abs(c) == float("inf"):
                raise ValueError(f"invalid stoichiometric coefficient for {sid!r}: {coeff!r}")
            cleaned[sid] = c
        if not any(c < 0 for c in cleaned.values()):
            raise ValueError("reaction must have at least one reactant (nu < 0)")
        if not any(c > 0 for c in cleaned.values()):
            raise ValueError("reaction must have at least one product (nu > 0)")
        return cleaned

    @model_validator(mode="after")
    def _atom_and_charge_balance(self) -> Reaction:
        unknown = set(self.nu) - set(self.species)
        if unknown:
            raise StoichiometryError(
                f"reaction references unknown species: {sorted(unknown)}",
                details={"unknown": sorted(unknown)},
            )
        atom_residual: dict[str, float] = defaultdict(float)
        charge_residual = 0.0
        for sid, coeff in self.nu.items():
            sp = self.species[sid]
            for element, count in sp.formula.items():
                atom_residual[element] += coeff * count
            charge_residual += coeff * sp.charge
        unbalanced = {el: res for el, res in atom_residual.items() if abs(res) > 1e-12}
        if unbalanced:
            raise StoichiometryError(
                "reaction is not atom-balanced",
                details={"element_residuals": unbalanced},
            )
        if abs(charge_residual) > 1e-12:
            raise StoichiometryError(
                "reaction is not charge-balanced",
                details={"charge_residual": charge_residual},
            )
        return self

    def reactant_ids(self) -> tuple[str, ...]:
        return tuple(sid for sid, c in self.nu.items() if c < 0)

    def product_ids(self) -> tuple[str, ...]:
        return tuple(sid for sid, c in self.nu.items() if c > 0)

    def apply_extent(self, composition: Composition, extent_mol: float) -> Composition:
        """Return new composition after reaction extent ξ (mol).

        ``n_i' = n_i + ν_i · ξ``. Raises if any amount would go negative.
        """
        xi = float(extent_mol)
        if xi != xi or abs(xi) == float("inf"):
            raise StoichiometryError(
                "extent_mol must be finite",
                details={"extent_mol": extent_mol},
            )
        new_amounts = dict(composition.amounts_mol)
        for sid, coeff in self.nu.items():
            base = new_amounts.get(sid, 0.0)
            updated = base + coeff * xi
            if updated < -1e-15:
                raise StoichiometryError(
                    f"extent {xi} drives species {sid!r} negative",
                    details={"species_id": sid, "amount": updated, "extent_mol": xi},
                )
            new_amounts[sid] = max(0.0, updated)
        # Drop species that were zero and never in nu? keep all touched + original
        return Composition(amounts_mol=new_amounts)

    def max_extent_mol(self, composition: Composition) -> float:
        """Largest non-negative extent limited by the scarcest reactant."""
        limits: list[float] = []
        for sid, coeff in self.nu.items():
            if coeff >= 0:
                continue
            n = composition.amounts_mol.get(sid, 0.0)
            limits.append(n / (-coeff))
        if not limits:
            return 0.0
        return max(0.0, min(limits))

    def atom_balance_check(
        self,
        *,
        atol: float = 1e-12,
        rtol: float = 0.0,
    ) -> dict[str, ConservationCheck]:
        """Re-evaluate per-element residuals through the conservation owner."""
        residuals: dict[str, float] = defaultdict(float)
        for sid, coeff in self.nu.items():
            sp = self.species[sid]
            for element, count in sp.formula.items():
                residuals[element] += coeff * count
        return {
            el: evaluate_residual(res, atol=atol, rtol=rtol, scale=1.0, unit="1")
            for el, res in residuals.items()
        }


def water_formation_reaction() -> Reaction:
    """Canonical 2 H2 + O2 → 2 H2O (gas-phase ideal example)."""
    h2 = Species(id="H2", name="Hydrogen", formula={"H": 2}, phase="g")
    o2 = Species(id="O2", name="Oxygen", formula={"O": 2}, phase="g")
    h2o = Species(id="H2O", name="Water", formula={"H": 2, "O": 1}, phase="g")
    return Reaction(
        id="water_formation",
        name="Hydrogen combustion / water formation",
        nu={"H2": -2.0, "O2": -1.0, "H2O": 2.0},
        species={"H2": h2, "O2": o2, "H2O": h2o},
    )


__all__ = ["Reaction", "water_formation_reaction"]
