"""P3 — 1D kinematics and mechanical energy.

Uniform-acceleration kinematics and the three classic mechanical energy
terms (kinetic, gravitational potential, work) are executed
:class:`~oec.physics.laws.PhysicalLaw` instances. A work-energy balance
closes the loop as an executed :class:`~oec.physics.laws.ConservationLaw`,
reported in **joules** — the actual unit of the mechanical energy balance,
not the domain-wide ``TOLERANCE_DEFAULTS`` force default (N), which applies
to a *force* balance, not an *energy* balance.
"""

from __future__ import annotations

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.laws import ConservationLaw, PhysicalLaw
from oec.physics.result import ConservationCheck
from oec.physics.types import PhysicsDomain, ValidityFrame
from oec.physics.units import as_canonical

STANDARD_GRAVITY = QuantityValue(value=9.80665, unit="m / s ** 2")

KINEMATICS_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="1D motion along a single axis", source="P3 v0"),
    Assumption(text="Constant (uniform) acceleration over the interval", source="P3 v0"),
    Assumption(text="Point-mass / rigid-body translation (no rotation)", source="P3 v0"),
)

ENERGY_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Point-mass mechanics; no rotational kinetic energy", source="P3 v0"),
    Assumption(
        text="Gravitational potential energy referenced to a fixed datum height", source="P3 v0"
    ),
)

_MECHANICS_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.MECHANICS,),
    description="1D kinematics and point-mass mechanical energy, per PHYSICS-CATALOG P3",
)

VELOCITY_LAW = PhysicalLaw(
    id="mechanics.kinematics.uniform_acceleration_velocity",
    name="Uniform-acceleration velocity (v = v0 + a t)",
    hypotheses=KINEMATICS_ASSUMPTIONS,
    validity=_MECHANICS_VALIDITY,
    references=("Serway & Jewett, Physics for Scientists and Engineers",),
    evaluator=lambda state: float(state["v0"] + state["a"] * state["t"]),
)

POSITION_LAW = PhysicalLaw(
    id="mechanics.kinematics.uniform_acceleration_position",
    name="Uniform-acceleration position (x = x0 + v0 t + 1/2 a t^2)",
    hypotheses=KINEMATICS_ASSUMPTIONS,
    validity=_MECHANICS_VALIDITY,
    references=("Serway & Jewett, Physics for Scientists and Engineers",),
    evaluator=lambda state: float(
        state["x0"] + state["v0"] * state["t"] + 0.5 * state["a"] * state["t"] ** 2
    ),
)

KINETIC_ENERGY_LAW = PhysicalLaw(
    id="mechanics.energy.kinetic",
    name="Translational kinetic energy (KE = 1/2 m v^2)",
    hypotheses=ENERGY_ASSUMPTIONS,
    validity=_MECHANICS_VALIDITY,
    references=("Serway & Jewett, Physics for Scientists and Engineers",),
    evaluator=lambda state: float(0.5 * state["mass"] * state["velocity"] ** 2),
)

POTENTIAL_ENERGY_LAW = PhysicalLaw(
    id="mechanics.energy.gravitational_potential",
    name="Gravitational potential energy (PE = m g h)",
    hypotheses=ENERGY_ASSUMPTIONS,
    validity=_MECHANICS_VALIDITY,
    references=("Serway & Jewett, Physics for Scientists and Engineers",),
    evaluator=lambda state: float(state["mass"] * state["gravity"] * state["height"]),
)

WORK_LAW = PhysicalLaw(
    id="mechanics.energy.work",
    name="Work done by a constant force along a displacement (W = F d)",
    hypotheses=(Assumption(text="Constant force aligned with the displacement", source="P3 v0"),),
    validity=_MECHANICS_VALIDITY,
    references=("Serway & Jewett, Physics for Scientists and Engineers",),
    evaluator=lambda state: float(state["force"] * state["displacement"]),
)

MECHANICAL_ENERGY_BALANCE_LAW = ConservationLaw(
    id="mechanics.energy.work_energy_balance",
    name="Work-energy balance (work in = change in KE + change in PE + losses)",
    hypotheses=(
        *ENERGY_ASSUMPTIONS,
        Assumption(text="Non-conservative losses, if any, are supplied explicitly", source="P3 v0"),
    ),
    validity=_MECHANICS_VALIDITY,
    references=("Serway & Jewett, Physics for Scientists and Engineers",),
    evaluator=lambda state: float(
        state["work_in"] - (state["delta_ke"] + state["delta_pe"] + state["losses"])
    ),
)


def uniform_acceleration_velocity(
    initial_velocity: QuantityValue, acceleration: QuantityValue, time: QuantityValue
) -> QuantityValue:
    """``v = v0 + a t`` via the executed :data:`VELOCITY_LAW`."""
    v0 = as_canonical(initial_velocity, "m / s")
    a = as_canonical(acceleration, "m / s ** 2")
    t = as_canonical(time, "s")
    value = VELOCITY_LAW.evaluate({"v0": v0.value, "a": a.value, "t": t.value})
    return QuantityValue(value=value, unit="m / s")


def uniform_acceleration_position(
    initial_position: QuantityValue,
    initial_velocity: QuantityValue,
    acceleration: QuantityValue,
    time: QuantityValue,
) -> QuantityValue:
    """``x = x0 + v0 t + 1/2 a t^2`` via the executed :data:`POSITION_LAW`."""
    x0 = as_canonical(initial_position, "m")
    v0 = as_canonical(initial_velocity, "m / s")
    a = as_canonical(acceleration, "m / s ** 2")
    t = as_canonical(time, "s")
    value = POSITION_LAW.evaluate({"x0": x0.value, "v0": v0.value, "a": a.value, "t": t.value})
    return QuantityValue(value=value, unit="m")


def kinetic_energy(mass: QuantityValue, velocity: QuantityValue) -> QuantityValue:
    """``KE = 1/2 m v^2`` via the executed :data:`KINETIC_ENERGY_LAW`."""
    m = as_canonical(mass, "kg")
    v = as_canonical(velocity, "m / s")
    value = KINETIC_ENERGY_LAW.evaluate({"mass": m.value, "velocity": v.value})
    return QuantityValue(value=value, unit="J")


def potential_energy(
    mass: QuantityValue, height: QuantityValue, gravity: QuantityValue = STANDARD_GRAVITY
) -> QuantityValue:
    """``PE = m g h`` via the executed :data:`POTENTIAL_ENERGY_LAW`."""
    m = as_canonical(mass, "kg")
    h = as_canonical(height, "m")
    g = as_canonical(gravity, "m / s ** 2")
    value = POTENTIAL_ENERGY_LAW.evaluate({"mass": m.value, "gravity": g.value, "height": h.value})
    return QuantityValue(value=value, unit="J")


def work_done(force: QuantityValue, displacement: QuantityValue) -> QuantityValue:
    """``W = F d`` via the executed :data:`WORK_LAW`."""
    f = as_canonical(force, "N")
    d = as_canonical(displacement, "m")
    value = WORK_LAW.evaluate({"force": f.value, "displacement": d.value})
    return QuantityValue(value=value, unit="J")


def mechanical_energy_balance(
    work_in: QuantityValue,
    delta_kinetic: QuantityValue,
    delta_potential: QuantityValue,
    losses: QuantityValue | None = None,
    *,
    atol: float = 1e-9,
    rtol: float = 1e-9,
) -> ConservationCheck:
    """Check the work-energy theorem: ``work_in == ΔKE + ΔPE + losses``.

    The residual is reported in joules (the real unit of a mechanical
    energy balance) rather than the domain-default N used for a force
    balance. Routed through the executed :data:`MECHANICAL_ENERGY_BALANCE_LAW`
    :class:`~oec.physics.laws.ConservationLaw`.
    """
    work = as_canonical(work_in, "J")
    d_ke = as_canonical(delta_kinetic, "J")
    d_pe = as_canonical(delta_potential, "J")
    loss = as_canonical(losses, "J") if losses is not None else QuantityValue(value=0.0, unit="J")

    scale = max(abs(work.value), abs(d_ke.value) + abs(d_pe.value) + abs(loss.value))
    return MECHANICAL_ENERGY_BALANCE_LAW.check(
        {
            "work_in": work.value,
            "delta_ke": d_ke.value,
            "delta_pe": d_pe.value,
            "losses": loss.value,
        },
        atol=atol,
        rtol=rtol,
        scale=scale,
        unit="J",
    )


__all__ = [
    "ENERGY_ASSUMPTIONS",
    "KINEMATICS_ASSUMPTIONS",
    "KINETIC_ENERGY_LAW",
    "MECHANICAL_ENERGY_BALANCE_LAW",
    "POSITION_LAW",
    "POTENTIAL_ENERGY_LAW",
    "STANDARD_GRAVITY",
    "VELOCITY_LAW",
    "WORK_LAW",
    "kinetic_energy",
    "mechanical_energy_balance",
    "potential_energy",
    "uniform_acceleration_position",
    "uniform_acceleration_velocity",
    "work_done",
]
