"""P4 — Bernoulli head, Darcy-Weisbach losses (f as input), and continuity.

The friction factor ``f`` is always an explicit **input** here: this module
does not derive it from Reynolds number, pipe roughness, or a Colebrook-type
correlation (that regime-dependent step is out of scope for v0 — see
PHYSICS-CATALOG "Regime / Reynolds / Colebrook"). Bernoulli head and mass
continuity are executed :class:`~oec.physics.laws.PhysicalLaw` instances; the
head balance (including losses) and the mass-flow continuity balance are
executed :class:`~oec.physics.laws.ConservationLaw` instances, each reported
in its real physical unit (m of head; kg/s of mass flow).
"""

from __future__ import annotations

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.laws import ConservationLaw, PhysicalLaw
from oec.physics.mechanics import STANDARD_GRAVITY
from oec.physics.result import ConservationCheck
from oec.physics.types import PhysicsDomain, ValidityFrame
from oec.physics.units import as_canonical

BERNOULLI_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(
        text="Incompressible, inviscid flow along a single streamline (ideal Bernoulli term)",
        source="P4 v0",
    ),
    Assumption(text="Steady flow", source="P4 v0"),
)

LOSSES_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(
        text="Darcy friction factor f is supplied as an input; no Reynolds/Colebrook regime"
        " determination is performed by this module",
        source="P4 v0",
    ),
    Assumption(text="Fully-developed flow in a straight pipe of constant diameter", source="P4 v0"),
)

CONTINUITY_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(
        text="Incompressible flow: density is constant between the two sections", source="P4 v0"
    ),
    Assumption(
        text="0D/1D control volume; no storage between sections (steady flow)", source="P4 v0"
    ),
)

_FLUIDS_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.FLUIDS,),
    description="0D/1D Bernoulli, Darcy-Weisbach losses (f input), continuity — PHYSICS-CATALOG P4",
)

BERNOULLI_HEAD_LAW = PhysicalLaw(
    id="fluids.bernoulli_head",
    name="Bernoulli head (pressure + velocity + elevation head)",
    hypotheses=BERNOULLI_ASSUMPTIONS,
    validity=_FLUIDS_VALIDITY,
    references=("White, Fluid Mechanics",),
    evaluator=lambda state: float(
        state["pressure"] / (state["density"] * state["gravity"])
        + state["velocity"] ** 2 / (2.0 * state["gravity"])
        + state["elevation"]
    ),
)

DARCY_WEISBACH_LOSS_LAW = PhysicalLaw(
    id="fluids.darcy_weisbach_head_loss",
    name="Darcy-Weisbach friction head loss (f as input)",
    hypotheses=LOSSES_ASSUMPTIONS,
    validity=_FLUIDS_VALIDITY,
    references=("White, Fluid Mechanics",),
    evaluator=lambda state: float(
        state["friction_factor"]
        * (state["length"] / state["diameter"])
        * state["velocity"] ** 2
        / (2.0 * state["gravity"])
    ),
)

MASS_FLOW_LAW = PhysicalLaw(
    id="fluids.continuity_mass_flow",
    name="Mass flow rate (ṁ = ρ A V)",
    hypotheses=CONTINUITY_ASSUMPTIONS,
    validity=_FLUIDS_VALIDITY,
    references=("White, Fluid Mechanics",),
    evaluator=lambda state: float(state["density"] * state["area"] * state["velocity"]),
)

BERNOULLI_BALANCE_LAW = ConservationLaw(
    id="fluids.bernoulli_balance_with_losses",
    name="Bernoulli head balance with friction losses (H1 = H2 + h_loss)",
    hypotheses=(*BERNOULLI_ASSUMPTIONS, *LOSSES_ASSUMPTIONS),
    validity=_FLUIDS_VALIDITY,
    references=("White, Fluid Mechanics",),
    evaluator=lambda state: float(
        state["head_upstream"] - state["head_downstream"] - state["head_loss"]
    ),
)

CONTINUITY_BALANCE_LAW = ConservationLaw(
    id="fluids.continuity_mass_balance",
    name="Mass-flow continuity balance (ṁ_in = ṁ_out)",
    hypotheses=CONTINUITY_ASSUMPTIONS,
    validity=_FLUIDS_VALIDITY,
    references=("White, Fluid Mechanics",),
    evaluator=lambda state: float(state["mass_flow_in"] - state["mass_flow_out"]),
)


def bernoulli_head(
    pressure: QuantityValue,
    velocity: QuantityValue,
    elevation: QuantityValue,
    density: QuantityValue,
    gravity: QuantityValue = STANDARD_GRAVITY,
) -> QuantityValue:
    """Bernoulli head ``H = p/(ρg) + v^2/(2g) + z`` via the executed :data:`BERNOULLI_HEAD_LAW`."""
    p = as_canonical(pressure, "Pa")
    v = as_canonical(velocity, "m / s")
    z = as_canonical(elevation, "m")
    rho = as_canonical(density, "kg / m ** 3")
    g = as_canonical(gravity, "m / s ** 2")
    value = BERNOULLI_HEAD_LAW.evaluate(
        {
            "pressure": p.value,
            "velocity": v.value,
            "elevation": z.value,
            "density": rho.value,
            "gravity": g.value,
        }
    )
    return QuantityValue(value=value, unit="m")


def darcy_weisbach_head_loss(
    friction_factor: float,
    length: QuantityValue,
    diameter: QuantityValue,
    velocity: QuantityValue,
    gravity: QuantityValue = STANDARD_GRAVITY,
) -> QuantityValue:
    """Darcy-Weisbach head loss ``h_L = f (L/D) v^2 / (2g)``.

    ``friction_factor`` is a required plain float **input** (dimensionless
    Darcy friction factor) — this function never derives it from Reynolds
    number or pipe roughness. Executes :data:`DARCY_WEISBACH_LOSS_LAW`.
    """
    if friction_factor < 0:
        raise ValueError("friction_factor must be non-negative")
    length_c = as_canonical(length, "m")
    diameter_c = as_canonical(diameter, "m")
    v = as_canonical(velocity, "m / s")
    g = as_canonical(gravity, "m / s ** 2")
    value = DARCY_WEISBACH_LOSS_LAW.evaluate(
        {
            "friction_factor": friction_factor,
            "length": length_c.value,
            "diameter": diameter_c.value,
            "velocity": v.value,
            "gravity": g.value,
        }
    )
    return QuantityValue(value=value, unit="m")


def continuity_mass_flow(
    density: QuantityValue, area: QuantityValue, velocity: QuantityValue
) -> QuantityValue:
    """Mass flow rate ``ṁ = ρ A V`` via the executed :data:`MASS_FLOW_LAW`."""
    rho = as_canonical(density, "kg / m ** 3")
    a = as_canonical(area, "m ** 2")
    v = as_canonical(velocity, "m / s")
    value = MASS_FLOW_LAW.evaluate({"density": rho.value, "area": a.value, "velocity": v.value})
    return QuantityValue(value=value, unit="kg / s")


def bernoulli_balance(
    head_upstream: QuantityValue,
    head_downstream: QuantityValue,
    head_loss: QuantityValue,
    *,
    atol: float = 1e-6,
    rtol: float = 1e-9,
) -> ConservationCheck:
    """Check ``H_upstream == H_downstream + h_loss`` (meters of head).

    Routed through the executed :data:`BERNOULLI_BALANCE_LAW`
    :class:`~oec.physics.laws.ConservationLaw`.
    """
    h1 = as_canonical(head_upstream, "m")
    h2 = as_canonical(head_downstream, "m")
    loss = as_canonical(head_loss, "m")
    scale = max(abs(h1.value), abs(h2.value))
    return BERNOULLI_BALANCE_LAW.check(
        {"head_upstream": h1.value, "head_downstream": h2.value, "head_loss": loss.value},
        atol=atol,
        rtol=rtol,
        scale=scale,
        unit="m",
    )


def continuity_balance(
    mass_flow_in: QuantityValue,
    mass_flow_out: QuantityValue,
    *,
    atol: float = 1e-9,
    rtol: float = 1e-9,
) -> ConservationCheck:
    """Check ``ṁ_in == ṁ_out`` (kg/s) via the executed :data:`CONTINUITY_BALANCE_LAW`."""
    m_in = as_canonical(mass_flow_in, "kg / s")
    m_out = as_canonical(mass_flow_out, "kg / s")
    scale = max(abs(m_in.value), abs(m_out.value))
    return CONTINUITY_BALANCE_LAW.check(
        {"mass_flow_in": m_in.value, "mass_flow_out": m_out.value},
        atol=atol,
        rtol=rtol,
        scale=scale,
        unit="kg / s",
    )


__all__ = [
    "BERNOULLI_ASSUMPTIONS",
    "BERNOULLI_BALANCE_LAW",
    "BERNOULLI_HEAD_LAW",
    "CONTINUITY_ASSUMPTIONS",
    "CONTINUITY_BALANCE_LAW",
    "DARCY_WEISBACH_LOSS_LAW",
    "LOSSES_ASSUMPTIONS",
    "MASS_FLOW_LAW",
    "bernoulli_balance",
    "bernoulli_head",
    "continuity_balance",
    "continuity_mass_flow",
    "darcy_weisbach_head_loss",
]
