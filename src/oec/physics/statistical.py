"""Statistical / thermal physics foundations (W3) — ideal gas.

Merit: ideal-gas law. Not kinetic theory distributions or statistical ensembles.
"""

from __future__ import annotations

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.errors import PhysicsEvaluationError
from oec.physics.laws import PhysicalLaw
from oec.physics.types import PhysicsDomain, ValidityFrame
from oec.physics.units import as_canonical

R_GAS = 8.314462618  # J/(mol K)

IDEAL_GAS_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Ideal gas; point particles, no interactions", source="W3 statphys v0"),
    Assumption(text="Equilibrium thermodynamic state", source="W3 statphys v0"),
)

_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.THERMAL,),
    description="Ideal-gas equation of state PV = nRT",
)

IDEAL_GAS_LAW = PhysicalLaw(
    id="statistical.ideal_gas",
    name="Ideal gas law P V = n R T",
    hypotheses=IDEAL_GAS_ASSUMPTIONS,
    validity=_VALIDITY,
    references=("Callen, Thermodynamics",),
    evaluator=lambda state: float(state["n"] * R_GAS * state["T"] / state["V"]),
)


def ideal_gas_pressure(
    amount_mol: float,
    temperature: QuantityValue,
    volume: QuantityValue,
) -> QuantityValue:
    """P = n R T / V."""
    n = float(amount_mol)
    t = as_canonical(temperature, "K")
    v = as_canonical(volume, "m ** 3")
    if n <= 0 or t.value <= 0 or v.value <= 0:
        raise PhysicsEvaluationError(
            "n, T, and V must be positive",
            details={"n": n, "T": t.value, "V": v.value},
        )
    p = IDEAL_GAS_LAW.evaluate({"n": n, "T": t.value, "V": v.value})
    return QuantityValue(value=p, unit="Pa")


def ideal_gas_volume(
    amount_mol: float,
    temperature: QuantityValue,
    pressure: QuantityValue,
) -> QuantityValue:
    """V = n R T / P."""
    n = float(amount_mol)
    t = as_canonical(temperature, "K")
    p = as_canonical(pressure, "Pa")
    if n <= 0 or t.value <= 0 or p.value <= 0:
        raise PhysicsEvaluationError(
            "n, T, and P must be positive",
            details={"n": n, "T": t.value, "P": p.value},
        )
    return QuantityValue(value=n * R_GAS * t.value / p.value, unit="m ** 3")


def rms_speed_monatomic(molar_mass_kg_per_mol: float, temperature: QuantityValue) -> QuantityValue:
    """v_rms = sqrt(3 R T / M) for ideal monatomic gas."""
    import math

    m = float(molar_mass_kg_per_mol)
    t = as_canonical(temperature, "K")
    if m <= 0 or t.value <= 0:
        raise PhysicsEvaluationError(
            "molar_mass and T must be positive",
            details={"M": m, "T": t.value},
        )
    return QuantityValue(value=math.sqrt(3.0 * R_GAS * t.value / m), unit="m / s")
