"""Wave foundations (W3) — phase speed, period/frequency, harmonic relations.

Merit: classical wave kinematics. Not continuum elastodynamics or acoustics CFD.
"""

from __future__ import annotations

import math

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.errors import PhysicsEvaluationError
from oec.physics.laws import PhysicalLaw
from oec.physics.types import PhysicsDomain, ValidityFrame
from oec.physics.units import as_canonical

WAVE_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Linear non-dispersive medium; constant phase speed", source="W3 waves v0"),
    Assumption(text="Monochromatic progressive wave (single frequency)", source="W3 waves v0"),
)

_WAVES_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.MECHANICS,),
    description="1D progressive wave kinematics (phase speed, period, wavelength)",
)

PHASE_SPEED_LAW = PhysicalLaw(
    id="waves.phase_speed",
    name="Phase speed v = f λ",
    hypotheses=WAVE_ASSUMPTIONS,
    validity=_WAVES_VALIDITY,
    references=("Halliday, Resnick, Krane — Waves",),
    evaluator=lambda state: float(state["frequency"] * state["wavelength"]),
)


def phase_speed(
    frequency: QuantityValue,
    wavelength: QuantityValue,
) -> QuantityValue:
    """v = f λ with SI conversion."""
    f = as_canonical(frequency, "Hz")
    lam = as_canonical(wavelength, "m")
    if f.value <= 0 or lam.value <= 0:
        raise PhysicsEvaluationError(
            "frequency and wavelength must be positive",
            details={"frequency": f.value, "wavelength": lam.value},
        )
    v = PHASE_SPEED_LAW.evaluate({"frequency": f.value, "wavelength": lam.value})
    return QuantityValue(value=v, unit="m / s")


def period_from_frequency(frequency: QuantityValue) -> QuantityValue:
    f = as_canonical(frequency, "Hz")
    if f.value <= 0:
        raise PhysicsEvaluationError("frequency must be positive", details={"frequency": f.value})
    return QuantityValue(value=1.0 / f.value, unit="s")


def angular_frequency(frequency: QuantityValue) -> QuantityValue:
    f = as_canonical(frequency, "Hz")
    if f.value <= 0:
        raise PhysicsEvaluationError("frequency must be positive", details={"frequency": f.value})
    return QuantityValue(value=2.0 * math.pi * f.value, unit="rad / s")


def wave_number(wavelength: QuantityValue) -> QuantityValue:
    lam = as_canonical(wavelength, "m")
    if lam.value <= 0:
        raise PhysicsEvaluationError(
            "wavelength must be positive", details={"wavelength": lam.value}
        )
    return QuantityValue(value=2.0 * math.pi / lam.value, unit="1 / m")
