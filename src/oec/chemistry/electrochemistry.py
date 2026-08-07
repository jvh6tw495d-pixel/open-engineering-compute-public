"""Generic cell electrochemistry — Nernst equation (v2.8 C4).

This is **not** the energy-based BESS SOC model in ``oec.physics.storage``.
It evaluates open-circuit cell voltage from a half-cell / cell reaction
quotient. No proprietary BTM product models.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field

from oec.chemistry.errors import ChemistryEvaluationError
from oec.chemistry.kinetics import R_GAS_J_PER_MOL_K
from oec.core.types import Assumption

# Faraday constant (CODATA-style engineering value)
F_FARADAY_C_PER_MOL = 96485.3321

NERNST_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Reversible cell; Nernst form at temperature T", source="chemistry.echem v0"),
    Assumption(text="Activities supplied as dimensionless Q", source="chemistry.echem v0"),
    Assumption(
        text="Not a pack/BESS energy model; see oec.physics.storage for SOC",
        source="chemistry.echem v0",
    ),
)


class NernstVoltage(BaseModel):
    """Open-circuit cell potential from the Nernst equation."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    e_v: float
    e0_v: float
    n_electrons: int = Field(ge=1)
    temperature_k: float = Field(gt=0.0)
    reaction_quotient: float = Field(gt=0.0)
    assumptions: tuple[Assumption, ...] = NERNST_ASSUMPTIONS


def nernst_potential_from_concentrations(
    *,
    e0_v: float,
    n_electrons: int,
    reactant_concentrations: dict[str, float],
    product_concentrations: dict[str, float],
    reactant_orders: dict[str, float] | None = None,
    product_orders: dict[str, float] | None = None,
    temperature_k: float = 298.15,
    c_ref_mol_m3: float = 1.0,
) -> NernstVoltage:
    """Nernst with Q built from concentrations: Q = Π (c_p/c°)α / Π (c_r/c°)β.

    Orders default to 1.0 for each listed species. Concentrations in mol/m³.
    """
    c_ref = float(c_ref_mol_m3)
    if not math.isfinite(c_ref) or c_ref <= 0.0:
        raise ChemistryEvaluationError("c_ref_mol_m3 must be positive finite")
    r_ord = reactant_orders or {k: 1.0 for k in reactant_concentrations}
    p_ord = product_orders or {k: 1.0 for k in product_concentrations}
    log_q = 0.0
    for sid, c in product_concentrations.items():
        cc = float(c)
        if not math.isfinite(cc) or cc <= 0.0:
            raise ChemistryEvaluationError(
                f"product concentration for {sid!r} must be positive",
                details={"species_id": sid},
            )
        log_q += float(p_ord.get(sid, 1.0)) * math.log(cc / c_ref)
    for sid, c in reactant_concentrations.items():
        cc = float(c)
        if not math.isfinite(cc) or cc <= 0.0:
            raise ChemistryEvaluationError(
                f"reactant concentration for {sid!r} must be positive",
                details={"species_id": sid},
            )
        log_q -= float(r_ord.get(sid, 1.0)) * math.log(cc / c_ref)
    q = math.exp(log_q)
    return nernst_potential(
        e0_v=e0_v,
        n_electrons=n_electrons,
        reaction_quotient=q,
        temperature_k=temperature_k,
    )


def nernst_potential(
    *,
    e0_v: float,
    n_electrons: int,
    reaction_quotient: float,
    temperature_k: float = 298.15,
    gas_constant: float = R_GAS_J_PER_MOL_K,
    faraday: float = F_FARADAY_C_PER_MOL,
) -> NernstVoltage:
    """E = E° − (RT / nF) · ln(Q).

    ``reaction_quotient`` is the dimensionless activity quotient for the
    cell reaction as written (products / reactants).
    """
    e0 = float(e0_v)
    n = int(n_electrons)
    q = float(reaction_quotient)
    t = float(temperature_k)
    r = float(gas_constant)
    f = float(faraday)
    for name, val in (
        ("e0_v", e0),
        ("reaction_quotient", q),
        ("temperature_k", t),
        ("gas_constant", r),
        ("faraday", f),
    ):
        if not math.isfinite(val):
            raise ChemistryEvaluationError(f"{name} must be finite", details={name: val})
    if n < 1:
        raise ChemistryEvaluationError("n_electrons must be >= 1", details={"n": n})
    if q <= 0.0:
        raise ChemistryEvaluationError(
            "reaction_quotient must be positive",
            details={"reaction_quotient": q},
        )
    if t <= 0.0:
        raise ChemistryEvaluationError("temperature_k must be positive")
    if r <= 0.0 or f <= 0.0:
        raise ChemistryEvaluationError("gas_constant and faraday must be positive")
    e = e0 - (r * t / (n * f)) * math.log(q)
    if not math.isfinite(e):
        raise ChemistryEvaluationError("nernst potential is not finite", details={"e": e})
    return NernstVoltage(
        e_v=e,
        e0_v=e0,
        n_electrons=n,
        temperature_k=t,
        reaction_quotient=q,
    )


__all__ = [
    "F_FARADAY_C_PER_MOL",
    "NERNST_ASSUMPTIONS",
    "NernstVoltage",
    "nernst_potential",
    "nernst_potential_from_concentrations",
]
