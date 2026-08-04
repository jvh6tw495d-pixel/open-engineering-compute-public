"""P4 Bernoulli, Darcy-Weisbach losses (f input), and continuity — Wave 3 slice 3.6."""

from __future__ import annotations

import pytest

from oec.kernel.units.quantity import QuantityValue
from oec.physics.fluids import (
    bernoulli_balance,
    bernoulli_head,
    continuity_balance,
    continuity_mass_flow,
    darcy_weisbach_head_loss,
)


def test_bernoulli_head_matches_hand_solved_value() -> None:
    # H = p/(rho g) + v^2/(2g) + z = 100000/(1000*9.80665) + 4^2/(2*9.80665) + 2
    head = bernoulli_head(
        pressure=QuantityValue(value=100_000.0, unit="Pa"),
        velocity=QuantityValue(value=4.0, unit="m / s"),
        elevation=QuantityValue(value=2.0, unit="m"),
        density=QuantityValue(value=1000.0, unit="kg / m ** 3"),
    )
    expected = 100_000.0 / (1000.0 * 9.80665) + 4.0**2 / (2 * 9.80665) + 2.0
    assert head.unit == "m"
    assert head.value == pytest.approx(expected)


def test_darcy_weisbach_head_loss_takes_friction_factor_as_input() -> None:
    # h_L = f (L/D) v^2/(2g) = 0.02 * (100/0.1) * 3^2 / (2*9.80665)
    loss = darcy_weisbach_head_loss(
        friction_factor=0.02,
        length=QuantityValue(value=100.0, unit="m"),
        diameter=QuantityValue(value=0.1, unit="m"),
        velocity=QuantityValue(value=3.0, unit="m / s"),
    )
    expected = 0.02 * (100.0 / 0.1) * 3.0**2 / (2 * 9.80665)
    assert loss.unit == "m"
    assert loss.value == pytest.approx(expected)


def test_darcy_weisbach_rejects_negative_friction_factor() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        darcy_weisbach_head_loss(
            friction_factor=-0.01,
            length=QuantityValue(value=1.0, unit="m"),
            diameter=QuantityValue(value=0.1, unit="m"),
            velocity=QuantityValue(value=1.0, unit="m / s"),
        )


def test_continuity_mass_flow_matches_hand_solved_value() -> None:
    # ṁ = rho A V = 1000 * 0.01 * 2 = 20 kg/s
    flow = continuity_mass_flow(
        density=QuantityValue(value=1000.0, unit="kg / m ** 3"),
        area=QuantityValue(value=0.01, unit="m ** 2"),
        velocity=QuantityValue(value=2.0, unit="m / s"),
    )
    assert flow.unit == "kg / s"
    assert flow.value == pytest.approx(20.0)


def test_bernoulli_balance_closes_when_loss_accounts_for_the_head_drop() -> None:
    check = bernoulli_balance(
        head_upstream=QuantityValue(value=12.0, unit="m"),
        head_downstream=QuantityValue(value=10.0, unit="m"),
        head_loss=QuantityValue(value=2.0, unit="m"),
    )
    assert check.unit == "m"
    assert check.balanced is True


def test_bernoulli_balance_flags_unaccounted_head_drop() -> None:
    check = bernoulli_balance(
        head_upstream=QuantityValue(value=12.0, unit="m"),
        head_downstream=QuantityValue(value=9.0, unit="m"),
        head_loss=QuantityValue(value=2.0, unit="m"),
    )
    assert check.residual == pytest.approx(1.0)
    assert check.balanced is False


def test_continuity_balance_is_balanced_for_matching_mass_flows() -> None:
    check = continuity_balance(
        mass_flow_in=QuantityValue(value=20.0, unit="kg / s"),
        mass_flow_out=QuantityValue(value=20.0, unit="kg / s"),
    )
    assert check.unit == "kg / s"
    assert check.balanced is True


def test_continuity_balance_flags_mismatched_mass_flows() -> None:
    check = continuity_balance(
        mass_flow_in=QuantityValue(value=20.0, unit="kg / s"),
        mass_flow_out=QuantityValue(value=15.0, unit="kg / s"),
    )
    assert check.balanced is False
