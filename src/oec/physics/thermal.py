"""P2 — 1D steady conduction and sensible heat capacity.

Two independent v0 models: Fourier's law of 1D steady conduction (an
executed :class:`~oec.physics.laws.PhysicalLaw`) and sensible thermal
storage (``Q = m c ΔT``). A steady-state energy balance closes the loop as
an executed :class:`~oec.physics.laws.ConservationLaw`, routed through the
:mod:`oec.physics.conservation` owner (D5) — never a locally reimplemented
tolerance check.
"""

from __future__ import annotations

from oec.core.types import Assumption
from oec.kernel.units.quantity import QuantityValue
from oec.physics.laws import ConservationLaw, PhysicalLaw
from oec.physics.result import ConservationCheck
from oec.physics.types import PhysicsDomain, ValidityFrame
from oec.physics.units import as_canonical
from oec.validation.base import Severity
from oec.validation.physical import require_above_absolute_zero

CONDUCTION_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="1D conduction along a single path (planar or rod)", source="P2 v0"),
    Assumption(text="Steady state; no internal heat generation", source="P2 v0"),
    Assumption(text="Thermal conductivity is constant over the conduction path", source="P2 v0"),
)

THERMAL_CAPACITY_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(text="Sensible heat only; no phase change", source="P2 v0"),
    Assumption(text="Specific heat is constant over the temperature range", source="P2 v0"),
)

_THERMAL_VALIDITY = ValidityFrame(
    domains=(PhysicsDomain.THERMAL,),
    description="1D conduction and sensible heat capacity, per PHYSICS-CATALOG P2",
)

FOURIER_CONDUCTION_LAW = PhysicalLaw(
    id="thermal.fourier_conduction_1d",
    name="Fourier's law of 1D steady conduction",
    hypotheses=CONDUCTION_ASSUMPTIONS,
    validity=_THERMAL_VALIDITY,
    references=("Incropera & DeWitt, Fundamentals of Heat and Mass Transfer",),
    evaluator=lambda state: float(state["k"] * state["area"] * state["delta_T"] / state["length"]),
)

SENSIBLE_HEAT_LAW = PhysicalLaw(
    id="thermal.sensible_heat_capacity",
    name="Sensible heat storage (Q = m c ΔT)",
    hypotheses=THERMAL_CAPACITY_ASSUMPTIONS,
    validity=_THERMAL_VALIDITY,
    references=("Incropera & DeWitt, Fundamentals of Heat and Mass Transfer",),
    evaluator=lambda state: float(state["mass"] * state["specific_heat"] * state["delta_T"]),
)

STEADY_THERMAL_BALANCE_LAW = ConservationLaw(
    id="thermal.steady_state_energy_balance",
    name="Steady-state thermal energy balance (no storage term)",
    hypotheses=(
        *CONDUCTION_ASSUMPTIONS,
        Assumption(
            text="No transient storage term (dT/dt = 0 at the balance boundary)", source="P2 v0"
        ),
    ),
    validity=_THERMAL_VALIDITY,
    references=("Incropera & DeWitt, Fundamentals of Heat and Mass Transfer",),
    evaluator=lambda state: float(state["heat_in"] - state["heat_out"]),
)


def _require_valid_temperature(field: str, temperature: QuantityValue) -> None:
    outcome = require_above_absolute_zero(field, temperature.value, temperature.unit)
    if outcome.severity != Severity.OK:
        raise ValueError("; ".join(outcome.messages))


def conduction_heat_rate(
    conductivity: QuantityValue,
    area: QuantityValue,
    length: QuantityValue,
    hot_temperature: QuantityValue,
    cold_temperature: QuantityValue,
) -> QuantityValue:
    """Steady 1D conduction heat rate ``Q = k * A * (T_hot - T_cold) / L``.

    Executes the :data:`FOURIER_CONDUCTION_LAW` :class:`PhysicalLaw`.
    Temperatures are converted to kelvin before subtracting so the delta is
    correct regardless of the input scale (degC, degF, K).
    """
    _require_valid_temperature("hot_temperature", hot_temperature)
    _require_valid_temperature("cold_temperature", cold_temperature)

    k = as_canonical(conductivity, "W / (m * K)")
    a = as_canonical(area, "m ** 2")
    length_c = as_canonical(length, "m")
    t_hot = as_canonical(hot_temperature, "K")
    t_cold = as_canonical(cold_temperature, "K")
    if t_hot.value < t_cold.value:
        raise ValueError("hot_temperature must be >= cold_temperature for a conduction heat rate")

    heat_rate = FOURIER_CONDUCTION_LAW.evaluate(
        {
            "k": k.value,
            "area": a.value,
            "length": length_c.value,
            "delta_T": t_hot.value - t_cold.value,
        }
    )
    return QuantityValue(value=heat_rate, unit="W")


def stored_thermal_energy(
    mass: QuantityValue,
    specific_heat: QuantityValue,
    hot_temperature: QuantityValue,
    cold_temperature: QuantityValue,
) -> QuantityValue:
    """Sensible heat stored/released, ``Q = m * c * ΔT``.

    Executes the :data:`SENSIBLE_HEAT_LAW` :class:`PhysicalLaw`.
    """
    _require_valid_temperature("hot_temperature", hot_temperature)
    _require_valid_temperature("cold_temperature", cold_temperature)

    mass_c = as_canonical(mass, "kg")
    specific_heat_c = as_canonical(specific_heat, "J / (kg * K)")
    t_hot = as_canonical(hot_temperature, "K")
    t_cold = as_canonical(cold_temperature, "K")

    energy = SENSIBLE_HEAT_LAW.evaluate(
        {
            "mass": mass_c.value,
            "specific_heat": specific_heat_c.value,
            "delta_T": t_hot.value - t_cold.value,
        }
    )
    return QuantityValue(value=energy, unit="J")


def steady_conduction_balance(
    heat_in: QuantityValue,
    heat_out: QuantityValue,
    *,
    atol: float = 1e-6,
    rtol: float = 1e-9,
) -> ConservationCheck:
    """Check ``heat_in == heat_out`` for a steady-state thermal boundary.

    The residual unit is watts (heat *rate*, not stored energy) — reconciled
    explicitly here rather than trusting the domain-wide ``TOLERANCE_DEFAULTS``,
    which are generic W defaults for the electrical/thermal power case and would
    be wrong for e.g. a stored-energy (J) balance. Routed through the executed
    :data:`STEADY_THERMAL_BALANCE_LAW` :class:`ConservationLaw`.
    """
    q_in = as_canonical(heat_in, "W")
    q_out = as_canonical(heat_out, "W")
    scale = max(abs(q_in.value), abs(q_out.value))
    return STEADY_THERMAL_BALANCE_LAW.check(
        {"heat_in": q_in.value, "heat_out": q_out.value},
        atol=atol,
        rtol=rtol,
        scale=scale,
        unit="W",
    )


__all__ = [
    "CONDUCTION_ASSUMPTIONS",
    "FOURIER_CONDUCTION_LAW",
    "SENSIBLE_HEAT_LAW",
    "STEADY_THERMAL_BALANCE_LAW",
    "THERMAL_CAPACITY_ASSUMPTIONS",
    "conduction_heat_rate",
    "steady_conduction_balance",
    "stored_thermal_energy",
]
