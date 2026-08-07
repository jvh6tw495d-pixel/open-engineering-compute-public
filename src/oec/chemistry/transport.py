"""Species transport / diffusion v0 (v2.8 wave-0 precondition).

1-D Fickian flux and a discrete two-node exchange step. This is **not**
hydraulics (P4 Bernoulli) and not multi-D CFD.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field

from oec.chemistry.errors import ChemistryEvaluationError
from oec.core.types import Assumption

TRANSPORT_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Isothermal, constant diffusivity D", source="chemistry.transport v0"),
    Assumption(text="Fick's first law in one spatial dimension", source="chemistry.transport v0"),
    Assumption(text="No advection / convection term in v0", source="chemistry.transport v0"),
)


class DiffusionFlux1D(BaseModel):
    """Result of J = −D · ∂c/∂x (finite difference)."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    flux_mol_per_m2_s: float
    diffusivity_m2_s: float = Field(gt=0.0)
    dc_dx_mol_per_m4: float
    assumptions: tuple[Assumption, ...] = TRANSPORT_ASSUMPTIONS


def fick_flux_1d(
    *,
    concentration_a_mol_m3: float,
    concentration_b_mol_m3: float,
    distance_m: float,
    diffusivity_m2_s: float,
) -> DiffusionFlux1D:
    """Finite-difference Fick flux from node A to node B.

    ``J_{A→B} = −D · (c_B − c_A) / Δx`` — positive flux means net moles
    leave A toward B when c_A > c_B.
    """
    ca = float(concentration_a_mol_m3)
    cb = float(concentration_b_mol_m3)
    dx = float(distance_m)
    d = float(diffusivity_m2_s)
    for name, val in (
        ("concentration_a_mol_m3", ca),
        ("concentration_b_mol_m3", cb),
        ("distance_m", dx),
        ("diffusivity_m2_s", d),
    ):
        if not math.isfinite(val):
            raise ChemistryEvaluationError(
                f"{name} must be finite",
                details={name: val},
            )
    if ca < 0.0 or cb < 0.0:
        raise ChemistryEvaluationError(
            "concentrations must be non-negative",
            details={"ca": ca, "cb": cb},
        )
    if dx <= 0.0:
        raise ChemistryEvaluationError(
            "distance_m must be positive",
            details={"distance_m": dx},
        )
    if d <= 0.0:
        raise ChemistryEvaluationError(
            "diffusivity_m2_s must be positive",
            details={"diffusivity_m2_s": d},
        )
    dc_dx = (cb - ca) / dx
    flux = -d * dc_dx
    return DiffusionFlux1D(
        flux_mol_per_m2_s=flux,
        diffusivity_m2_s=d,
        dc_dx_mol_per_m4=dc_dx,
    )


def two_node_diffusion_step(
    *,
    amount_a_mol: float,
    amount_b_mol: float,
    volume_a_m3: float,
    volume_b_m3: float,
    area_m2: float,
    distance_m: float,
    diffusivity_m2_s: float,
    dt_s: float,
) -> tuple[float, float, float]:
    """Explicit Euler exchange between two well-mixed nodes.

    Returns ``(n_a', n_b', moles_transferred_a_to_b)``.
    Mass is conserved: n_a' + n_b' == n_a + n_b (within float).
    """
    na = float(amount_a_mol)
    nb = float(amount_b_mol)
    va = float(volume_a_m3)
    vb = float(volume_b_m3)
    area = float(area_m2)
    dt = float(dt_s)
    for name, val in (
        ("amount_a_mol", na),
        ("amount_b_mol", nb),
        ("volume_a_m3", va),
        ("volume_b_m3", vb),
        ("area_m2", area),
        ("dt_s", dt),
    ):
        if not math.isfinite(val):
            raise ChemistryEvaluationError(f"{name} must be finite", details={name: val})
    if na < 0.0 or nb < 0.0:
        raise ChemistryEvaluationError("amounts must be non-negative")
    if va <= 0.0 or vb <= 0.0 or area <= 0.0 or dt < 0.0:
        raise ChemistryEvaluationError(
            "volumes, area must be > 0 and dt_s >= 0",
            details={"va": va, "vb": vb, "area": area, "dt": dt},
        )
    ca = na / va
    cb = nb / vb
    flux = fick_flux_1d(
        concentration_a_mol_m3=ca,
        concentration_b_mol_m3=cb,
        distance_m=distance_m,
        diffusivity_m2_s=diffusivity_m2_s,
    ).flux_mol_per_m2_s
    # Positive flux (A→B) removes moles from A
    delta = flux * area * dt
    # Clip so neither node goes negative
    if delta > na:
        delta = na
    if -delta > nb:
        delta = -nb
    return na - delta, nb + delta, delta


__all__ = [
    "TRANSPORT_ASSUMPTIONS",
    "DiffusionFlux1D",
    "fick_flux_1d",
    "two_node_diffusion_step",
]
