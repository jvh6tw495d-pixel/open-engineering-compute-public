"""P2 conduction and thermal capacity — Wave 3 slice 3.4."""

from __future__ import annotations

import pytest

from oec.kernel.units.quantity import QuantityValue
from oec.physics.thermal import (
    conduction_heat_rate,
    steady_conduction_balance,
    stored_thermal_energy,
)


def test_conduction_heat_rate_matches_hand_solved_fourier_law() -> None:
    # Q = k A dT / L = 0.5 * 2.0 * 20 / 0.1 = 200 W
    q = conduction_heat_rate(
        conductivity=QuantityValue(value=0.5, unit="W / (m * K)"),
        area=QuantityValue(value=2.0, unit="m ** 2"),
        length=QuantityValue(value=0.1, unit="m"),
        hot_temperature=QuantityValue(value=40.0, unit="degC"),
        cold_temperature=QuantityValue(value=20.0, unit="degC"),
    )
    assert q.unit == "W"
    assert q.value == pytest.approx(200.0)


def test_conduction_heat_rate_rejects_reversed_temperature_gradient() -> None:
    with pytest.raises(ValueError, match=">="):
        conduction_heat_rate(
            conductivity=QuantityValue(value=0.5, unit="W / (m * K)"),
            area=QuantityValue(value=1.0, unit="m ** 2"),
            length=QuantityValue(value=1.0, unit="m"),
            hot_temperature=QuantityValue(value=10.0, unit="degC"),
            cold_temperature=QuantityValue(value=20.0, unit="degC"),
        )


def test_conduction_heat_rate_rejects_temperature_at_or_below_absolute_zero() -> None:
    with pytest.raises(ValueError, match="absolute zero"):
        conduction_heat_rate(
            conductivity=QuantityValue(value=0.5, unit="W / (m * K)"),
            area=QuantityValue(value=1.0, unit="m ** 2"),
            length=QuantityValue(value=1.0, unit="m"),
            hot_temperature=QuantityValue(value=-300.0, unit="degC"),
            cold_temperature=QuantityValue(value=-320.0, unit="degC"),
        )


def test_stored_thermal_energy_matches_hand_solved_sensible_heat() -> None:
    # Q = m c dT = 2.0 kg * 4186 J/(kg K) * 10 K = 83720 J
    q = stored_thermal_energy(
        mass=QuantityValue(value=2.0, unit="kg"),
        specific_heat=QuantityValue(value=4186.0, unit="J / (kg * K)"),
        hot_temperature=QuantityValue(value=30.0, unit="degC"),
        cold_temperature=QuantityValue(value=20.0, unit="degC"),
    )
    assert q.unit == "J"
    assert q.value == pytest.approx(83720.0)


def test_steady_conduction_balance_is_balanced_for_matching_heat_rates() -> None:
    check = steady_conduction_balance(
        heat_in=QuantityValue(value=200.0, unit="W"),
        heat_out=QuantityValue(value=200.0 + 1e-8, unit="W"),
    )
    assert check.unit == "W"
    assert check.balanced is True


def test_steady_conduction_balance_flags_mismatched_heat_rates() -> None:
    check = steady_conduction_balance(
        heat_in=QuantityValue(value=200.0, unit="W"),
        heat_out=QuantityValue(value=150.0, unit="W"),
    )
    assert check.residual == pytest.approx(50.0)
    assert check.balanced is False
