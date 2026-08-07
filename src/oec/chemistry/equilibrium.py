"""Simplified chemical equilibrium (v2.8 C2).

Uses concentration-based reaction quotient Qc and a supplied equilibrium
constant Kc (ideal, isothermal). No full Gibbs free-energy minimisation
in v0 — that remains future work.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field

from oec.chemistry.errors import ChemistryEvaluationError
from oec.chemistry.species import Composition
from oec.chemistry.stoichiometry import Reaction
from oec.core.types import Assumption

EQUILIBRIUM_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Ideal mixture; activities ≈ concentrations / c°", source="chemistry.eq v0"),
    Assumption(text="Isothermal; Kc provided (not computed from ΔG°)", source="chemistry.eq v0"),
    Assumption(text="Single reaction; no competing pathways", source="chemistry.eq v0"),
)


class ReactionQuotient(BaseModel):
    """Qc evaluation for a reaction at a composition."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    qc: float = Field(gt=0.0)
    kc: float = Field(gt=0.0)
    driving_force: float  # ln(Qc/Kc); <0 means forward-favored when Q<K
    at_equilibrium: bool
    assumptions: tuple[Assumption, ...] = EQUILIBRIUM_ASSUMPTIONS


def reaction_quotient_concentration(
    reaction: Reaction,
    composition: Composition,
    *,
    volume_m3: float,
    c_ref_mol_m3: float = 1.0,
) -> float:
    """Qc = Π (c_i / c°)ν_i  with c_i = n_i / V."""
    v = float(volume_m3)
    c_ref = float(c_ref_mol_m3)
    if not math.isfinite(v) or v <= 0.0:
        raise ChemistryEvaluationError(
            "volume_m3 must be finite and positive",
            details={"volume_m3": volume_m3},
        )
    if not math.isfinite(c_ref) or c_ref <= 0.0:
        raise ChemistryEvaluationError(
            "c_ref_mol_m3 must be finite and positive",
            details={"c_ref_mol_m3": c_ref_mol_m3},
        )
    # Handle vanishing species first (Q → 0 if any product is missing with ν>0;
    # Q → +∞ if any reactant is missing with ν<0 while products exist).
    for sid, nu in reaction.nu.items():
        n = composition.amounts_mol.get(sid, 0.0)
        c = n / v
        if c <= 0.0:
            if nu > 0:
                return 0.0
            # reactant exhausted → forward Q unbounded
            return float("inf")

    log_q = 0.0
    for sid, nu in reaction.nu.items():
        n = composition.amounts_mol.get(sid, 0.0)
        c = n / v
        log_q += nu * math.log(c / c_ref)
    q = math.exp(log_q)
    if not math.isfinite(q) or q <= 0.0:
        raise ChemistryEvaluationError(
            "reaction quotient is not a positive finite number",
            details={"qc": q},
        )
    return q


def evaluate_equilibrium(
    reaction: Reaction,
    composition: Composition,
    *,
    kc: float,
    volume_m3: float,
    c_ref_mol_m3: float = 1.0,
    rtol: float = 1e-6,
) -> ReactionQuotient:
    """Compare Qc to Kc; report ln(Qc/Kc) and near-equilibrium flag."""
    k = float(kc)
    if not math.isfinite(k) or k <= 0.0:
        raise ChemistryEvaluationError(
            "kc must be finite and positive",
            details={"kc": kc},
        )
    qc = reaction_quotient_concentration(
        reaction,
        composition,
        volume_m3=volume_m3,
        c_ref_mol_m3=c_ref_mol_m3,
    )
    if qc == float("inf"):
        # Reactant exhausted — reverse-favored extreme
        return ReactionQuotient(
            qc=1e300,
            kc=k,
            driving_force=math.log(1e300 / k),
            at_equilibrium=False,
        )
    if qc <= 0.0:
        # Pure forward drive (missing product)
        return ReactionQuotient(
            qc=1e-300,
            kc=k,
            driving_force=math.log(1e-300 / k),
            at_equilibrium=False,
        )
    drive = math.log(qc / k)
    at_eq = abs(drive) <= rtol
    return ReactionQuotient(qc=qc, kc=k, driving_force=drive, at_equilibrium=at_eq)


def reaction_quotient_mole_fraction(
    reaction: Reaction,
    composition: Composition,
) -> float:
    """Qx = Π x_i^{ν_i} for ideal solutions (activity ≈ mole fraction)."""
    total = composition.total_mol
    if total <= 0.0:
        raise ChemistryEvaluationError("composition total must be positive for mole fractions")
    log_q = 0.0
    for sid, nu in reaction.nu.items():
        n = composition.amounts_mol.get(sid, 0.0)
        if n <= 0.0:
            if nu > 0:
                return 0.0
            return float("inf")
        x = n / total
        log_q += nu * math.log(x)
    q = math.exp(log_q)
    if not math.isfinite(q) or q <= 0.0:
        raise ChemistryEvaluationError("mole-fraction quotient is not positive finite")
    return q


def kp_from_kc(
    *,
    kc: float,
    delta_n_gas: float,
    temperature_k: float,
    gas_constant: float = 8.314462618,
    p_ref_pa: float = 101325.0,
) -> float:
    """Ideal-gas conversion Kp = Kc · (RT / p°)Δn  (SI: c in mol/m³, p in Pa).

    ``delta_n_gas`` is Σ ν_i for gas-phase species in the reaction as written.
    """
    k = float(kc)
    dn = float(delta_n_gas)
    t = float(temperature_k)
    r = float(gas_constant)
    p_ref = float(p_ref_pa)
    for name, val in (
        ("kc", k),
        ("delta_n_gas", dn),
        ("temperature_k", t),
        ("gas_constant", r),
        ("p_ref_pa", p_ref),
    ):
        if not math.isfinite(val):
            raise ChemistryEvaluationError(f"{name} must be finite", details={name: val})
    if k <= 0.0 or t <= 0.0 or r <= 0.0 or p_ref <= 0.0:
        raise ChemistryEvaluationError("kc, T, R, p_ref must be positive")
    return float(k * (r * t / p_ref) ** dn)


def gas_delta_n(reaction: Reaction) -> float:
    """Σ ν_i over species with phase ``g`` (0 if phase unset — not counted as gas)."""
    total = 0.0
    for sid, nu in reaction.nu.items():
        sp = reaction.species[sid]
        if sp.phase == "g":
            total += float(nu)
    return float(total)


def equilibrium_constant_from_delta_g(
    *,
    delta_g_j_per_mol: float,
    temperature_k: float,
    gas_constant: float = 8.314462618,
) -> float:
    """Simplified Gibbs link: K = exp(−ΔG° / RT) (ideal, single reaction).

    This is **not** a multi-species Gibbs free-energy minimiser. It only
    converts a supplied standard free-energy change into an equilibrium
    constant for use with :func:`evaluate_equilibrium`.
    """
    dg = float(delta_g_j_per_mol)
    t = float(temperature_k)
    r = float(gas_constant)
    for name, val in (
        ("delta_g_j_per_mol", dg),
        ("temperature_k", t),
        ("gas_constant", r),
    ):
        if not math.isfinite(val):
            raise ChemistryEvaluationError(f"{name} must be finite", details={name: val})
    if t <= 0.0 or r <= 0.0:
        raise ChemistryEvaluationError("temperature_k and gas_constant must be positive")
    k = math.exp(-dg / (r * t))
    if not math.isfinite(k) or k <= 0.0:
        raise ChemistryEvaluationError(
            "equilibrium constant from ΔG is not positive finite",
            details={"k": k},
        )
    return k


def extent_to_equilibrium_binary(
    reaction: Reaction,
    composition: Composition,
    *,
    kc: float,
    volume_m3: float,
    c_ref_mol_m3: float = 1.0,
    tol: float = 1e-10,
    max_iter: int = 80,
) -> float:
    """Bisection on extent for single-reaction equilibrium (0 ≤ ξ ≤ ξ_max).

    Suitable when Qc is monotonic in ξ (standard mass-action form).
    """
    xi_lo = 0.0
    xi_hi = reaction.max_extent_mol(composition)
    if xi_hi <= 0.0:
        return 0.0

    def drive(xi: float) -> float:
        comp = reaction.apply_extent(composition, xi)
        return evaluate_equilibrium(
            reaction,
            comp,
            kc=kc,
            volume_m3=volume_m3,
            c_ref_mol_m3=c_ref_mol_m3,
        ).driving_force

    d0 = drive(xi_lo)
    d1 = drive(xi_hi)
    # If already past equilibrium at xi=0 (Q>K), return 0
    if d0 >= 0.0:
        return 0.0
    # If still Q<K at max extent, take max
    if d1 <= 0.0:
        return xi_hi

    lo, hi = xi_lo, xi_hi
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if drive(mid) < 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


__all__ = [
    "EQUILIBRIUM_ASSUMPTIONS",
    "ReactionQuotient",
    "equilibrium_constant_from_delta_g",
    "evaluate_equilibrium",
    "extent_to_equilibrium_binary",
    "gas_delta_n",
    "kp_from_kc",
    "reaction_quotient_concentration",
    "reaction_quotient_mole_fraction",
]
