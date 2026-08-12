"""W3 physics foundations: waves, optics, EM, ideal gas."""

from __future__ import annotations

import pytest

from oec.kernel.units.quantity import QuantityValue
from oec.physics.electromagnetism import coulomb_force, parallel_plate_capacitance
from oec.physics.optics import snell_refracted_angle, thin_lens_image_distance
from oec.physics.statistical import ideal_gas_pressure
from oec.physics.waves import phase_speed


def test_phase_speed() -> None:
    v = phase_speed(
        QuantityValue(value=50.0, unit="Hz"),
        QuantityValue(value=6.0, unit="m"),
    )
    assert v.value == pytest.approx(300.0)


def test_snell_and_tir() -> None:
    out = snell_refracted_angle(1.0, 1.5, 0.5)
    assert out["total_internal_reflection"] is False
    assert out["theta2_rad"] is not None
    assert out["theta2_rad"] < 0.5
    tir = snell_refracted_angle(1.5, 1.0, 1.2)
    assert tir["total_internal_reflection"] is True
    assert tir["theta2_rad"] is None


def test_thin_lens_symmetric() -> None:
    # u = 2f → v = 2f
    v = thin_lens_image_distance(0.1, 0.2)
    assert v == pytest.approx(0.2)


def test_coulomb_and_capacitor() -> None:
    f = coulomb_force(
        QuantityValue(value=1e-6, unit="C"),
        QuantityValue(value=1e-6, unit="C"),
        QuantityValue(value=0.1, unit="m"),
    )
    assert f.value == pytest.approx(0.898755179, rel=1e-6)
    c = parallel_plate_capacitance(
        QuantityValue(value=0.01, unit="m**2"),
        QuantityValue(value=0.001, unit="m"),
    )
    assert c.value == pytest.approx(8.8541878128e-11, rel=1e-9)


def test_ideal_gas_near_stp() -> None:
    p = ideal_gas_pressure(
        1.0,
        QuantityValue(value=273.15, unit="K"),
        QuantityValue(value=0.0224, unit="m**3"),
    )
    # ~1 atm
    assert p.value == pytest.approx(101325.0, rel=0.02)
