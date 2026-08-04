"""P3 kinematics and mechanical energy — Wave 3 slice 3.5."""

from __future__ import annotations

import pytest

from oec.kernel.units.quantity import QuantityValue
from oec.physics.mechanics import (
    kinetic_energy,
    mechanical_energy_balance,
    potential_energy,
    uniform_acceleration_position,
    uniform_acceleration_velocity,
    work_done,
)


def test_uniform_acceleration_velocity_matches_hand_solved_kinematics() -> None:
    # v = v0 + a t = 2 + 3*4 = 14 m/s
    v = uniform_acceleration_velocity(
        initial_velocity=QuantityValue(value=2.0, unit="m / s"),
        acceleration=QuantityValue(value=3.0, unit="m / s ** 2"),
        time=QuantityValue(value=4.0, unit="s"),
    )
    assert v.unit == "m / s"
    assert v.value == pytest.approx(14.0)


def test_uniform_acceleration_position_matches_hand_solved_kinematics() -> None:
    # x = x0 + v0 t + 0.5 a t^2 = 0 + 2*4 + 0.5*3*16 = 8 + 24 = 32 m
    x = uniform_acceleration_position(
        initial_position=QuantityValue(value=0.0, unit="m"),
        initial_velocity=QuantityValue(value=2.0, unit="m / s"),
        acceleration=QuantityValue(value=3.0, unit="m / s ** 2"),
        time=QuantityValue(value=4.0, unit="s"),
    )
    assert x.unit == "m"
    assert x.value == pytest.approx(32.0)


def test_kinetic_energy_matches_hand_solved_value() -> None:
    # KE = 0.5 * 10 * 5^2 = 125 J
    ke = kinetic_energy(
        mass=QuantityValue(value=10.0, unit="kg"), velocity=QuantityValue(value=5.0, unit="m / s")
    )
    assert ke.unit == "J"
    assert ke.value == pytest.approx(125.0)


def test_potential_energy_uses_standard_gravity_by_default() -> None:
    # PE = m g h = 2 * 9.80665 * 10 = 196.133 J
    pe = potential_energy(
        mass=QuantityValue(value=2.0, unit="kg"), height=QuantityValue(value=10.0, unit="m")
    )
    assert pe.unit == "J"
    assert pe.value == pytest.approx(196.133, rel=1e-6)


def test_work_done_matches_hand_solved_value() -> None:
    w = work_done(
        force=QuantityValue(value=50.0, unit="N"), displacement=QuantityValue(value=3.0, unit="m")
    )
    assert w.unit == "J"
    assert w.value == pytest.approx(150.0)


def test_mechanical_energy_balance_is_balanced_for_a_conservative_free_fall() -> None:
    # No external work: gravity is internal to the KE/PE split, so gain in
    # KE must equal loss in PE (delta_pe negative) for the balance to close.
    mass = QuantityValue(value=1.0, unit="kg")
    height = QuantityValue(value=5.0, unit="m")
    pe_initial = potential_energy(mass, height)
    velocity_final = QuantityValue(value=(2 * 9.80665 * 5.0) ** 0.5, unit="m / s")
    ke_final = kinetic_energy(mass, velocity_final)

    check = mechanical_energy_balance(
        work_in=QuantityValue(value=0.0, unit="J"),
        delta_kinetic=ke_final,
        delta_potential=QuantityValue(value=-pe_initial.value, unit="J"),
    )
    assert check.unit == "J"
    assert check.balanced is True


def test_mechanical_energy_balance_reports_energy_unit_not_force_default() -> None:
    check = mechanical_energy_balance(
        work_in=QuantityValue(value=100.0, unit="J"),
        delta_kinetic=QuantityValue(value=40.0, unit="J"),
        delta_potential=QuantityValue(value=40.0, unit="J"),
    )
    assert check.unit == "J"
    assert check.residual == pytest.approx(20.0)
    assert check.balanced is False


def test_mechanical_energy_balance_accounts_for_explicit_losses() -> None:
    check = mechanical_energy_balance(
        work_in=QuantityValue(value=100.0, unit="J"),
        delta_kinetic=QuantityValue(value=60.0, unit="J"),
        delta_potential=QuantityValue(value=0.0, unit="J"),
        losses=QuantityValue(value=40.0, unit="J"),
    )
    assert check.balanced is True
