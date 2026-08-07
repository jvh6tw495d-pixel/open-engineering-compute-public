"""Sequential multi-reaction extent network (v0).

Applies a list of reactions in order with given extents. This is **not**
a simultaneous Gibbs free-energy minimiser — only ordered stoichiometric
updates for mechanism-like bookkeeping.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from oec.chemistry.errors import ChemistryEvaluationError, StoichiometryError
from oec.chemistry.species import Composition
from oec.chemistry.stoichiometry import Reaction


class ReactionStep(BaseModel):
    """One reaction + extent to apply."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reaction: Reaction
    extent_mol: float = Field(description="Extent ξ for this step (mol)")


class NetworkResult(BaseModel):
    """Composition after sequential extent applications."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    composition: Composition
    extents_applied: tuple[float, ...]
    intermediate_amounts: tuple[dict[str, float], ...]


def apply_reaction_network(
    composition: Composition,
    steps: list[ReactionStep],
) -> NetworkResult:
    """Apply reactions in order; each step uses the latest composition."""
    if not steps:
        raise ChemistryEvaluationError("reaction network requires at least one step")
    comp = composition
    extents: list[float] = []
    snapshots: list[dict[str, float]] = [dict(comp.amounts_mol)]
    for step in steps:
        xi = float(step.extent_mol)
        if not (xi == xi) or abs(xi) == float("inf"):  # NaN/inf
            raise ChemistryEvaluationError("extent_mol must be finite")
        try:
            comp = step.reaction.apply_extent(comp, xi)
        except StoichiometryError as exc:
            raise ChemistryEvaluationError(
                f"network step {step.reaction.id!r} failed: {exc.message}",
                details={"reaction_id": step.reaction.id, **exc.details},
            ) from exc
        extents.append(xi)
        snapshots.append(dict(comp.amounts_mol))
    return NetworkResult(
        composition=comp,
        extents_applied=tuple(extents),
        intermediate_amounts=tuple(snapshots),
    )


__all__ = ["NetworkResult", "ReactionStep", "apply_reaction_network"]
