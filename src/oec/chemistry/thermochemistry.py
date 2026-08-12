"""Thermochemistry foundations (W3) — van't Hoff K(T) and Hess-style ΔH sum.

Merit: classical physical chemistry. No full Gibbs minimiser (ADR 0029).
"""

from __future__ import annotations

import math

from oec.chemistry.errors import ChemistryEvaluationError
from oec.chemistry.kinetics import R_GAS_J_PER_MOL_K
from oec.core.types import Assumption

THERMOCHEM_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(
        text="ΔH° approximately constant between T1 and T2 (integrated van't Hoff)",
        source="W3 thermochem v0",
    ),
    Assumption(
        text="Ideal-solution / ideal-gas equilibrium constant form", source="W3 thermochem v0"
    ),
)


def vanthoff_k2(
    *,
    k1: float,
    t1_k: float,
    t2_k: float,
    delta_h_j_per_mol: float,
    r_gas: float = R_GAS_J_PER_MOL_K,
) -> dict[str, float | tuple[Assumption, ...]]:
    """K2 = K1 exp[-ΔH/R (1/T2 - 1/T1)].

    Temperatures in kelvin; ΔH in J/mol (endothermic positive).
    """
    if k1 <= 0:
        raise ChemistryEvaluationError("k1 must be positive", details={"k1": k1})
    if t1_k <= 0 or t2_k <= 0:
        raise ChemistryEvaluationError(
            "temperatures must be positive kelvin",
            details={"t1_k": t1_k, "t2_k": t2_k},
        )
    if r_gas <= 0:
        raise ChemistryEvaluationError("r_gas must be positive")
    ln_k2 = math.log(k1) - (delta_h_j_per_mol / r_gas) * (1.0 / t2_k - 1.0 / t1_k)
    k2 = math.exp(ln_k2)
    if not math.isfinite(k2) or k2 <= 0:
        raise ChemistryEvaluationError("computed k2 is not positive finite", details={"k2": k2})
    return {
        "k1": float(k1),
        "k2": float(k2),
        "t1_k": float(t1_k),
        "t2_k": float(t2_k),
        "delta_h_j_per_mol": float(delta_h_j_per_mol),
        "ln_k2_over_k1": float(ln_k2 - math.log(k1)),
        "assumptions": THERMOCHEM_ASSUMPTIONS,
    }


def hess_reaction_enthalpy(
    steps: list[dict[str, float]],
) -> dict[str, float | int | tuple[Assumption, ...]]:
    """Σ ν_i ΔH_i for elementary steps.

    Each step: ``{"delta_h_j_per_mol": float, "coefficient": float}``
    where coefficient is the stoichiometric multiplier of that half-reaction
    as written (negative if reversed).
    """
    if not steps:
        raise ChemistryEvaluationError("steps must be non-empty")
    total = 0.0
    for i, step in enumerate(steps):
        dh = float(step.get("delta_h_j_per_mol", "nan"))
        coef = float(step.get("coefficient", 1.0))
        if not math.isfinite(dh) or not math.isfinite(coef):
            raise ChemistryEvaluationError(
                f"step {i} has non-finite delta_h or coefficient",
                details={"step": step},
            )
        total += coef * dh
    return {
        "delta_h_j_per_mol": float(total),
        "n_steps": len(steps),
        "assumptions": (
            Assumption(
                text="Hess's law: state function path independence of ΔH",
                source="W3 thermochem v0",
            ),
        ),
    }
