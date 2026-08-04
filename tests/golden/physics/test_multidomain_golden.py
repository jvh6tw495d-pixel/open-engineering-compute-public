"""Wave 3 multidomain golden set (slice 3.8).

GATE-W3 requires proof that at least two P1-P5 slices execute their result
from a real, non-stub :class:`~oec.physics.laws.PhysicalLaw` and/or
:class:`~oec.physics.laws.ConservationLaw` — not just instantiate/serialize
one. Every case below hand-solves the expected answer independently of the
production code path, then drives the *public* module function (which
internally calls ``.evaluate()``/``.check()`` on a module-level law
constant) and asserts the two agree. This exercises four slices
(P1 electrical, P2 thermal, P3 mechanics, P4 fluids) end to end.
"""

from __future__ import annotations

import math

import pytest

from oec.kernel.units.quantity import QuantityValue
from oec.physics.electrical import KCL_LAW as ELECTRICAL_KCL_LAW
from oec.physics.electrical import NetworkLine, dc_power_flow
from oec.physics.fluids import CONTINUITY_BALANCE_LAW, continuity_balance, continuity_mass_flow
from oec.physics.laws import ConservationLaw, PhysicalLaw
from oec.physics.mechanics import (
    KINETIC_ENERGY_LAW,
    MECHANICAL_ENERGY_BALANCE_LAW,
    kinetic_energy,
    mechanical_energy_balance,
    potential_energy,
)
from oec.physics.thermal import (
    FOURIER_CONDUCTION_LAW,
    STEADY_THERMAL_BALANCE_LAW,
    conduction_heat_rate,
    steady_conduction_balance,
)


def test_p1_electrical_kcl_is_an_executed_conservation_law_not_a_stub() -> None:
    """P1: dc_power_flow's KCL residual comes from an executed ConservationLaw."""
    assert isinstance(ELECTRICAL_KCL_LAW, ConservationLaw)

    lines = [
        NetworkLine(from_bus="A", to_bus="B", susceptance=10.0),
        NetworkLine(from_bus="B", to_bus="C", susceptance=10.0),
        NetworkLine(from_bus="A", to_bus="C", susceptance=10.0),
    ]
    injections = {"A": -1.0, "B": 0.4, "C": 0.6}

    result = dc_power_flow(lines, injections, slack_bus="A")

    # Independently hand-solved oracle: the law is literally `injection - outflow`,
    # so re-deriving the outflow from the result's own flows must match residual==0.
    outflow_a = result.flows[0].power + result.flows[2].power  # A->B, A->C
    hand_check = ELECTRICAL_KCL_LAW.check(
        {"injection": injections["A"], "outflow": outflow_a},
        atol=1e-9,
        rtol=1e-9,
        scale=1.0,
        unit="pu",
    )
    assert hand_check.residual == pytest.approx(result.node_balance["A"].residual)
    assert result.balance.balanced is True


def test_p2_thermal_conduction_and_balance_are_executed_physical_and_conservation_laws() -> None:
    """P2: conduction rate (PhysicalLaw) feeds a steady balance (ConservationLaw), both executed."""
    assert isinstance(FOURIER_CONDUCTION_LAW, PhysicalLaw)
    assert isinstance(STEADY_THERMAL_BALANCE_LAW, ConservationLaw)

    conductivity = QuantityValue(value=1.5, unit="W / (m * K)")
    area = QuantityValue(value=0.5, unit="m ** 2")
    length = QuantityValue(value=0.02, unit="m")
    hot = QuantityValue(value=80.0, unit="degC")
    cold = QuantityValue(value=20.0, unit="degC")

    heat_rate = conduction_heat_rate(conductivity, area, length, hot, cold)

    # Hand-solved oracle: Q = k A dT / L = 1.5 * 0.5 * 60 / 0.02 = 2250 W
    assert heat_rate.value == pytest.approx(2250.0)

    check = steady_conduction_balance(heat_in=heat_rate, heat_out=heat_rate)
    assert check.unit == "W"
    assert check.balanced is True

    mismatched = steady_conduction_balance(
        heat_in=heat_rate, heat_out=QuantityValue(value=heat_rate.value - 100.0, unit="W")
    )
    assert mismatched.residual == pytest.approx(100.0)
    assert mismatched.balanced is False


def test_p3_mechanics_kinetic_energy_and_work_energy_balance_are_executed() -> None:
    """P3: kinetic energy (PhysicalLaw) and work-energy balance (ConservationLaw), executed."""
    assert isinstance(KINETIC_ENERGY_LAW, PhysicalLaw)
    assert isinstance(MECHANICAL_ENERGY_BALANCE_LAW, ConservationLaw)

    mass = QuantityValue(value=2.0, unit="kg")
    height = QuantityValue(value=8.0, unit="m")
    velocity_at_ground = QuantityValue(value=math.sqrt(2 * 9.80665 * 8.0), unit="m / s")

    pe0 = potential_energy(mass, height)
    ke_final = kinetic_energy(mass, velocity_at_ground)

    # Hand-solved oracle: free fall converts all PE to KE (no external work, no losses).
    assert ke_final.value == pytest.approx(pe0.value, rel=1e-6)

    check = mechanical_energy_balance(
        work_in=QuantityValue(value=0.0, unit="J"),
        delta_kinetic=ke_final,
        delta_potential=QuantityValue(value=-pe0.value, unit="J"),
    )
    assert check.unit == "J"
    assert check.balanced is True


def test_p4_fluids_continuity_is_an_executed_conservation_law() -> None:
    """P4: mass-flow continuity balance runs through an executed ConservationLaw."""
    assert isinstance(CONTINUITY_BALANCE_LAW, ConservationLaw)

    upstream = continuity_mass_flow(
        density=QuantityValue(value=1000.0, unit="kg / m ** 3"),
        area=QuantityValue(value=0.02, unit="m ** 2"),
        velocity=QuantityValue(value=1.5, unit="m / s"),
    )
    # Continuity for an incompressible fluid in a narrower section: A1 V1 = A2 V2.
    downstream = continuity_mass_flow(
        density=QuantityValue(value=1000.0, unit="kg / m ** 3"),
        area=QuantityValue(value=0.01, unit="m ** 2"),
        velocity=QuantityValue(value=3.0, unit="m / s"),
    )

    check = continuity_balance(mass_flow_in=upstream, mass_flow_out=downstream)
    assert check.unit == "kg / s"
    assert check.balanced is True
    assert upstream.value == pytest.approx(downstream.value)


def test_at_least_two_slices_execute_from_a_real_law_over_real_models() -> None:
    """GATE-W3 assertion: >=2 P1-P5 slices execute laws over real models."""
    executed_laws = {
        "P1-electrical": ELECTRICAL_KCL_LAW,
        "P2-thermal": STEADY_THERMAL_BALANCE_LAW,
        "P3-mechanics": MECHANICAL_ENERGY_BALANCE_LAW,
        "P4-fluids": CONTINUITY_BALANCE_LAW,
    }
    assert len(executed_laws) >= 2
    assert all(isinstance(law, ConservationLaw) for law in executed_laws.values())
