"""Unit tests for generic PV model v0 (v2.6.1 Wave 1 step 1.3)."""

from __future__ import annotations

import pytest

from oec.physics.pv import PV_ASSUMPTIONS, pv_energy_from_series, pv_power


def test_pv_power_basic_product() -> None:
    """P = G × A × η without temperature correction."""
    # 800 W/m² × 10 m² × 0.2 = 1600 W
    out = pv_power(800.0, 10.0, 0.2)
    assert out["power"] == pytest.approx(1600.0)
    assert out["temperature_factor"] == pytest.approx(1.0)
    assert out["efficiency_effective"] == pytest.approx(0.2)
    assert out["irradiance"] == 800.0
    assert out["area"] == 10.0
    assert out["efficiency"] == 0.2


def test_pv_power_zero_irradiance() -> None:
    out = pv_power(0.0, 5.0, 0.18)
    assert out["power"] == pytest.approx(0.0)


def test_pv_power_optional_temperature_correction() -> None:
    """P = G × A × η × (1 + γ · (T − T_ref))."""
    g, a, eta = 1000.0, 2.0, 0.2
    gamma = -0.004  # 1/°C
    t_cell = 45.0
    t_ref = 25.0
    f_temp = 1.0 + gamma * (t_cell - t_ref)  # 0.92
    expected = g * a * eta * f_temp  # 368 W

    out = pv_power(
        g,
        a,
        eta,
        temperature=t_cell,
        temperature_coefficient=gamma,
        reference_temperature=t_ref,
    )
    assert out["temperature_factor"] == pytest.approx(f_temp)
    assert out["efficiency_effective"] == pytest.approx(eta * f_temp)
    assert out["power"] == pytest.approx(expected)


def test_pv_power_temperature_correction_at_reference_is_unity() -> None:
    out = pv_power(
        1000.0,
        1.0,
        0.15,
        temperature=25.0,
        temperature_coefficient=-0.004,
        reference_temperature=25.0,
    )
    assert out["temperature_factor"] == pytest.approx(1.0)
    assert out["power"] == pytest.approx(150.0)


def test_pv_power_rejects_partial_temperature_args() -> None:
    with pytest.raises(ValueError, match="both be provided"):
        pv_power(1000.0, 1.0, 0.2, temperature=40.0)
    with pytest.raises(ValueError, match="both be provided"):
        pv_power(1000.0, 1.0, 0.2, temperature_coefficient=-0.004)


def test_pv_power_rejects_invalid_geometry() -> None:
    with pytest.raises(ValueError, match="irradiance must be non-negative"):
        pv_power(-1.0, 1.0, 0.2)
    with pytest.raises(ValueError, match="area must be positive"):
        pv_power(100.0, 0.0, 0.2)
    with pytest.raises(ValueError, match="efficiency must be in"):
        pv_power(100.0, 1.0, 0.0)
    with pytest.raises(ValueError, match="efficiency must be in"):
        pv_power(100.0, 1.0, 1.1)


def test_pv_energy_from_precomputed_powers() -> None:
    # 100 W × 1 h + 200 W × 1 h = 300 Wh
    out = pv_energy_from_series([100.0, 200.0], dt_hours=1.0)
    assert out["n"] == 2
    assert out["power"] == pytest.approx([100.0, 200.0])
    assert out["interval_energy"] == pytest.approx([100.0, 200.0])
    assert out["total_energy"] == pytest.approx(300.0)
    assert out["dt_hours"] == pytest.approx([1.0, 1.0])
    assert "temperature_factor" not in out


def test_pv_energy_from_series_per_step_dt() -> None:
    out = pv_energy_from_series([10.0, 20.0], dt_hours=[1.0, 0.5])
    assert out["interval_energy"] == pytest.approx([10.0, 10.0])
    assert out["total_energy"] == pytest.approx(20.0)


def test_pv_energy_from_irradiance_series() -> None:
    # G = [500, 1000], A=2, η=0.2 → P = [200, 400]; dt=1 → E_total=600
    out = pv_energy_from_series(
        irradiance=[500.0, 1000.0],
        area=2.0,
        efficiency=0.2,
        dt_hours=1.0,
    )
    assert out["power"] == pytest.approx([200.0, 400.0])
    assert out["total_energy"] == pytest.approx(600.0)
    assert out["temperature_factor"] == pytest.approx([1.0, 1.0])


def test_pv_energy_from_irradiance_with_temperature_series() -> None:
    gamma = -0.004
    # step 0: T=25 → f=1; step 1: T=45 → f=0.92
    out = pv_energy_from_series(
        irradiance=[1000.0, 1000.0],
        area=1.0,
        efficiency=0.2,
        dt_hours=1.0,
        temperatures=[25.0, 45.0],
        temperature_coefficient=gamma,
    )
    assert out["temperature_factor"] == pytest.approx([1.0, 0.92])
    assert out["power"] == pytest.approx([200.0, 184.0])
    assert out["total_energy"] == pytest.approx(384.0)


def test_pv_energy_from_irradiance_scalar_temperature() -> None:
    out = pv_energy_from_series(
        irradiance=[1000.0, 500.0],
        area=1.0,
        efficiency=0.2,
        dt_hours=2.0,
        temperatures=45.0,
        temperature_coefficient=-0.004,
    )
    f = 0.92
    assert out["temperature_factor"] == pytest.approx([f, f])
    assert out["power"] == pytest.approx([200.0 * f, 100.0 * f])
    assert out["total_energy"] == pytest.approx((200.0 * f + 100.0 * f) * 2.0)


def test_pv_energy_from_series_empty() -> None:
    out = pv_energy_from_series([], dt_hours=1.0)
    assert out["n"] == 0
    assert out["power"] == []
    assert out["interval_energy"] == []
    assert out["total_energy"] == 0.0


def test_pv_energy_from_series_rejects_both_or_neither() -> None:
    with pytest.raises(ValueError, match="either powers or irradiance, not both"):
        pv_energy_from_series([1.0], irradiance=[1.0], area=1.0, efficiency=0.2)
    with pytest.raises(ValueError, match="either powers or irradiance series"):
        pv_energy_from_series()


def test_pv_energy_from_series_rejects_dt_length_mismatch() -> None:
    with pytest.raises(ValueError, match="dt_hours sequence length"):
        pv_energy_from_series([1.0, 2.0], dt_hours=[1.0])


def test_pv_energy_from_series_rejects_negative_dt() -> None:
    with pytest.raises(ValueError, match="dt_hours"):
        pv_energy_from_series([1.0], dt_hours=-0.5)


def test_pv_energy_irradiance_path_requires_area_and_efficiency() -> None:
    with pytest.raises(ValueError, match="requires area and efficiency"):
        pv_energy_from_series(irradiance=[100.0], area=1.0)
    with pytest.raises(ValueError, match="requires area and efficiency"):
        pv_energy_from_series(irradiance=[100.0], efficiency=0.2)


def test_pv_energy_precomputed_rejects_geometry_and_temp_kwargs() -> None:
    with pytest.raises(ValueError, match="irradiance path"):
        pv_energy_from_series([1.0], area=1.0, efficiency=0.2)
    with pytest.raises(ValueError, match="temperature correction"):
        pv_energy_from_series([1.0], temperature_coefficient=-0.004)


def test_pv_assumptions_are_explicit() -> None:
    """Wave 1 accept: PV v0 hypotheses are listed."""
    assert len(PV_ASSUMPTIONS) >= 3
    texts = " ".join(a.text.lower() for a in PV_ASSUMPTIONS)
    assert "irradiance" in texts or "g" in texts
    assert "temperature" in texts
    assert "inverter" in texts or "soiling" in texts
    sources = {a.source for a in PV_ASSUMPTIONS}
    assert "PV v0" in sources
