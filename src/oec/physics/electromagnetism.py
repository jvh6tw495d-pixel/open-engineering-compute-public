"""Electromagnetism foundations (W3) — Coulomb and parallel-plate capacitor.

Merit: vacuum electrostatics / electrostatic approximation. Not full Maxwell
solver, magnetostatics multipoles, or circuit SPICE.
"""

from __future__ import annotations

import math

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.errors import PhysicsEvaluationError
from oec.physics.laws import PhysicalLaw
from oec.physics.types import PhysicsDomain, ValidityFrame
from oec.physics.units import as_canonical

# Vacuum permittivity (CODATA common engineering value)
EPS0 = 8.8541878128e-12  # F/m
K_COULOMB = 1.0 / (4.0 * math.pi * EPS0)  # N m^2 / C^2

EM_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(
        text="Vacuum (or εr=1); point charges / parallel-plate idealization", source="W3 em v0"
    ),
    Assumption(text="Electrostatic quasi-static approximation", source="W3 em v0"),
)

_EM_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.ELECTRICAL,),
    description="Vacuum electrostatics: Coulomb force and parallel-plate capacitor",
)

COULOMB_LAW = PhysicalLaw(
    id="em.coulomb",
    name="Coulomb force magnitude F = k |q1 q2| / r^2",
    hypotheses=EM_ASSUMPTIONS,
    validity=_EM_VALIDITY,
    references=("Griffiths, Introduction to Electrodynamics",),
    evaluator=lambda state: float(K_COULOMB * abs(state["q1"] * state["q2"]) / (state["r"] ** 2)),
)

CAPACITOR_LAW = PhysicalLaw(
    id="em.parallel_plate_capacitance",
    name="Parallel-plate capacitance C = ε0 A / d",
    hypotheses=EM_ASSUMPTIONS,
    validity=_EM_VALIDITY,
    references=("Griffiths, Introduction to Electrodynamics",),
    evaluator=lambda state: float(EPS0 * state["area"] / state["gap"]),
)


def coulomb_force(
    charge1: QuantityValue,
    charge2: QuantityValue,
    separation: QuantityValue,
) -> QuantityValue:
    q1 = as_canonical(charge1, "C")
    q2 = as_canonical(charge2, "C")
    r = as_canonical(separation, "m")
    if r.value <= 0:
        raise PhysicsEvaluationError("separation must be positive", details={"r": r.value})
    f = COULOMB_LAW.evaluate({"q1": q1.value, "q2": q2.value, "r": r.value})
    return QuantityValue(value=f, unit="N")


def parallel_plate_capacitance(
    area: QuantityValue,
    gap: QuantityValue,
    relative_permittivity: float = 1.0,
) -> QuantityValue:
    a = as_canonical(area, "m ** 2")
    d = as_canonical(gap, "m")
    er = float(relative_permittivity)
    if a.value <= 0 or d.value <= 0 or er <= 0:
        raise PhysicsEvaluationError(
            "area, gap, and relative_permittivity must be positive",
            details={"area": a.value, "gap": d.value, "er": er},
        )
    c = EPS0 * er * a.value / d.value
    return QuantityValue(value=c, unit="F")


def parallel_plate_field(voltage: QuantityValue, gap: QuantityValue) -> QuantityValue:
    """Uniform field magnitude E = V / d between infinite plates."""
    v = as_canonical(voltage, "V")
    d = as_canonical(gap, "m")
    if d.value <= 0:
        raise PhysicsEvaluationError("gap must be positive", details={"gap": d.value})
    return QuantityValue(value=abs(v.value) / d.value, unit="V / m")


def capacitor_energy(capacitance: QuantityValue, voltage: QuantityValue) -> QuantityValue:
    """U = 1/2 C V^2."""
    c = as_canonical(capacitance, "F")
    v = as_canonical(voltage, "V")
    if c.value < 0:
        raise PhysicsEvaluationError("capacitance must be non-negative")
    return QuantityValue(value=0.5 * c.value * (v.value**2), unit="J")
