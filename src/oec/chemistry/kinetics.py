"""Arrhenius kinetics and isothermal batch extent step (v2.8 C3)."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field

from oec.chemistry.errors import ChemistryEvaluationError
from oec.chemistry.species import Composition
from oec.chemistry.stoichiometry import Reaction
from oec.core.types import Assumption

# CODATA / IUPAC common value used in engineering tables
R_GAS_J_PER_MOL_K = 8.314462618

KINETICS_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Arrhenius form k = A · exp(−Ea / RT)", source="chemistry.kinetics v0"),
    Assumption(text="Ideal isothermal batch; well-mixed", source="chemistry.kinetics v0"),
    Assumption(text="Power-law rate in concentrations", source="chemistry.kinetics v0"),
)


class ArrheniusRate(BaseModel):
    """Evaluated rate constant at temperature T."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    k: float = Field(gt=0.0)
    temperature_k: float = Field(gt=0.0)
    pre_exponential: float = Field(gt=0.0)
    activation_energy_j_per_mol: float = Field(ge=0.0)
    assumptions: tuple[Assumption, ...] = KINETICS_ASSUMPTIONS


def arrhenius_rate_constant(
    *,
    pre_exponential: float,
    activation_energy_j_per_mol: float,
    temperature_k: float,
    gas_constant: float = R_GAS_J_PER_MOL_K,
) -> ArrheniusRate:
    """k(T) = A · exp(−Ea / (R T))."""
    a = float(pre_exponential)
    ea = float(activation_energy_j_per_mol)
    t = float(temperature_k)
    r = float(gas_constant)
    for name, val in (
        ("pre_exponential", a),
        ("activation_energy_j_per_mol", ea),
        ("temperature_k", t),
        ("gas_constant", r),
    ):
        if not math.isfinite(val):
            raise ChemistryEvaluationError(f"{name} must be finite", details={name: val})
    if a <= 0.0:
        raise ChemistryEvaluationError("pre_exponential must be positive")
    if ea < 0.0:
        raise ChemistryEvaluationError("activation_energy_j_per_mol must be >= 0")
    if t <= 0.0:
        raise ChemistryEvaluationError("temperature_k must be positive")
    if r <= 0.0:
        raise ChemistryEvaluationError("gas_constant must be positive")
    k = a * math.exp(-ea / (r * t))
    if not math.isfinite(k) or k <= 0.0:
        raise ChemistryEvaluationError(
            "arrhenius evaluation produced non-positive k",
            details={"k": k},
        )
    return ArrheniusRate(
        k=k,
        temperature_k=t,
        pre_exponential=a,
        activation_energy_j_per_mol=ea,
    )


def power_law_rate(
    *,
    k: float,
    concentrations_mol_m3: dict[str, float],
    orders: dict[str, float],
) -> float:
    """r = k · Π c_i^{α_i}  (mol / m³ / s when consistent units)."""
    kk = float(k)
    if not math.isfinite(kk) or kk < 0.0:
        raise ChemistryEvaluationError("k must be finite and >= 0", details={"k": k})
    rate = kk
    for sid, order in orders.items():
        c = float(concentrations_mol_m3.get(sid, 0.0))
        alpha = float(order)
        if not math.isfinite(c) or c < 0.0:
            raise ChemistryEvaluationError(
                f"concentration for {sid!r} must be finite and >= 0",
                details={"species_id": sid, "c": c},
            )
        if not math.isfinite(alpha):
            raise ChemistryEvaluationError(f"order for {sid!r} must be finite")
        if c == 0.0 and alpha > 0.0:
            return 0.0
        if c == 0.0 and alpha < 0.0:
            raise ChemistryEvaluationError(
                f"zero concentration with negative order for {sid!r}",
                details={"species_id": sid},
            )
        rate *= c**alpha
    if not math.isfinite(rate):
        raise ChemistryEvaluationError("rate is not finite", details={"rate": rate})
    return rate


class BatchExtentStep(BaseModel):
    """One explicit Euler step of reaction extent in a constant-volume batch."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    extent_step_mol: float
    rate_mol_per_m3_s: float
    composition: Composition
    dt_s: float = Field(ge=0.0)


def batch_extent_euler_step(
    reaction: Reaction,
    composition: Composition,
    *,
    k: float,
    orders: dict[str, float],
    volume_m3: float,
    dt_s: float,
) -> BatchExtentStep:
    """ξ ← ξ + r · V · Δt  with r from power-law kinetics; clip at ξ_max."""
    v = float(volume_m3)
    dt = float(dt_s)
    if not math.isfinite(v) or v <= 0.0:
        raise ChemistryEvaluationError("volume_m3 must be finite and positive")
    if not math.isfinite(dt) or dt < 0.0:
        raise ChemistryEvaluationError("dt_s must be finite and >= 0")
    conc = composition.concentrations_mol_per_m3(v)
    rate = power_law_rate(k=k, concentrations_mol_m3=conc, orders=orders)
    dxi = rate * v * dt
    xi_max = reaction.max_extent_mol(composition)
    dxi = min(max(0.0, dxi), xi_max)
    new_comp = reaction.apply_extent(composition, dxi)
    return BatchExtentStep(
        extent_step_mol=dxi,
        rate_mol_per_m3_s=rate,
        composition=new_comp,
        dt_s=dt,
    )


__all__ = [
    "KINETICS_ASSUMPTIONS",
    "R_GAS_J_PER_MOL_K",
    "ArrheniusRate",
    "BatchExtentStep",
    "arrhenius_rate_constant",
    "batch_extent_euler_step",
    "power_law_rate",
]
