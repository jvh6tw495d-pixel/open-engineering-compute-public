"""P1 optional light THD v0 (D7) — Wave 3 slice 3.3."""

from __future__ import annotations

import math

import pytest

from oec.kernel.units.quantity import QuantityValue
from oec.physics.errors import PhysicsEvaluationError
from oec.physics.harmonics import total_harmonic_distortion


def test_thd_matches_hand_solved_ratio() -> None:
    # THD = sqrt(3^2 + 4^2) / 100 = 5 / 100 = 0.05
    thd = total_harmonic_distortion(
        fundamental=QuantityValue(value=100.0, unit="V"),
        harmonics=[QuantityValue(value=3.0, unit="V"), QuantityValue(value=4.0, unit="V")],
    )
    assert thd == pytest.approx(0.05)


def test_thd_converts_mixed_units_before_the_ratio() -> None:
    thd_mixed = total_harmonic_distortion(
        fundamental=QuantityValue(value=100.0, unit="V"),
        harmonics=[QuantityValue(value=3000.0, unit="mV"), QuantityValue(value=4000.0, unit="mV")],
    )
    thd_same_unit = total_harmonic_distortion(
        fundamental=QuantityValue(value=100.0, unit="V"),
        harmonics=[QuantityValue(value=3.0, unit="V"), QuantityValue(value=4.0, unit="V")],
    )
    assert thd_mixed == pytest.approx(thd_same_unit)


def test_thd_zero_harmonics_content_is_zero() -> None:
    thd = total_harmonic_distortion(
        fundamental=QuantityValue(value=230.0, unit="V"),
        harmonics=[QuantityValue(value=0.0, unit="V")],
    )
    assert thd == pytest.approx(0.0)


def test_thd_rejects_nonpositive_fundamental() -> None:
    with pytest.raises(PhysicsEvaluationError, match="positive"):
        total_harmonic_distortion(
            fundamental=QuantityValue(value=0.0, unit="V"),
            harmonics=[QuantityValue(value=1.0, unit="V")],
        )


def test_thd_rejects_empty_harmonics() -> None:
    with pytest.raises(PhysicsEvaluationError, match="at least one"):
        total_harmonic_distortion(fundamental=QuantityValue(value=100.0, unit="V"), harmonics=[])


def test_thd_matches_direct_math_formula_for_several_harmonics() -> None:
    fundamental = 120.0
    harmonics = [5.0, 3.0, 2.0, 1.0]
    expected = math.sqrt(sum(h**2 for h in harmonics)) / fundamental

    thd = total_harmonic_distortion(
        fundamental=QuantityValue(value=fundamental, unit="A"),
        harmonics=[QuantityValue(value=h, unit="A") for h in harmonics],
    )
    assert thd == pytest.approx(expected)
