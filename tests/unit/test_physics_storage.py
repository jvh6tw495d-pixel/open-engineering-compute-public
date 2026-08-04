"""Unit tests for energy-based storage SOC (v2.6.1 Wave 1 step 1.1)."""

from __future__ import annotations

import inspect

import pytest

from oec.kernel.energy.metrics import soc_update
from oec.physics.storage import energy_based_soc_update, storage_trajectory


def test_energy_based_soc_update_parity_with_kernel_charge_step() -> None:
    """Golden charge: 0.5 + 10 W × 1 h / 100 Wh → SOC 0.6 (legacy skill input)."""
    kwargs = {
        "soc": 0.5,
        "power": 10.0,
        "dt_hours": 1.0,
        "capacity": 100.0,
    }
    kernel = soc_update(**kwargs)
    physics = energy_based_soc_update(**kwargs)

    assert physics == kernel
    assert physics["soc"] == pytest.approx(0.6)
    assert physics["delta_soc"] == pytest.approx(0.1)
    assert physics["energy_delta"] == pytest.approx(10.0)
    assert physics["clipped"] is False


def test_energy_based_soc_update_parity_with_efficiencies() -> None:
    kwargs = {
        "soc": 0.5,
        "power": 20.0,
        "dt_hours": 1.0,
        "capacity": 100.0,
        "efficiency_charge": 0.98,
        "efficiency_discharge": 0.95,
    }
    assert energy_based_soc_update(**kwargs) == soc_update(**kwargs)

    discharge = {
        "soc": 0.5,
        "power": -20.0,
        "dt_hours": 1.0,
        "capacity": 100.0,
        "efficiency_charge": 0.98,
        "efficiency_discharge": 0.95,
    }
    # Discharge: delta_e = power * dt / η_d = -20 / 0.95
    expected_delta_e = -20.0 / 0.95
    out = energy_based_soc_update(**discharge)
    assert out == soc_update(**discharge)
    assert out["energy_delta"] == pytest.approx(expected_delta_e)
    assert out["soc"] == pytest.approx(0.5 + expected_delta_e / 100.0)


def test_energy_based_soc_update_clips_to_unit_interval() -> None:
    over = energy_based_soc_update(soc=0.95, power=20.0, dt_hours=1.0, capacity=100.0)
    assert over["soc"] == 1.0
    assert over["clipped"] is True
    assert over == soc_update(soc=0.95, power=20.0, dt_hours=1.0, capacity=100.0)

    under = energy_based_soc_update(soc=0.05, power=-20.0, dt_hours=1.0, capacity=100.0)
    assert under["soc"] == 0.0
    assert under["clipped"] is True
    assert under == soc_update(soc=0.05, power=-20.0, dt_hours=1.0, capacity=100.0)


def test_energy_based_soc_update_rejects_invalid_inputs_like_kernel() -> None:
    with pytest.raises(ValueError, match="capacity must be positive"):
        energy_based_soc_update(0.5, 1.0, 1.0, 0.0)
    with pytest.raises(ValueError, match="soc must be in"):
        energy_based_soc_update(1.5, 1.0, 1.0, 100.0)
    with pytest.raises(ValueError, match="efficiencies"):
        energy_based_soc_update(0.5, 1.0, 1.0, 100.0, efficiency_charge=0.0)


def test_storage_trajectory_multi_step_matches_sequential_updates() -> None:
    powers = [10.0, -5.0, 15.0]
    capacity = 100.0
    dt = 1.0
    eta_c, eta_d = 0.95, 0.9

    traj = storage_trajectory(
        0.5,
        powers,
        dt,
        capacity,
        efficiency_charge=eta_c,
        efficiency_discharge=eta_d,
    )

    assert traj["soc_path"][0] == pytest.approx(0.5)
    assert len(traj["soc"]) == 3
    assert len(traj["delta_soc"]) == 3
    assert len(traj["energy_delta"]) == 3
    assert len(traj["clipped"]) == 3
    assert traj["any_clipped"] is False
    assert traj["soc_final"] == traj["soc"][-1]

    current = 0.5
    for i, power in enumerate(powers):
        step = energy_based_soc_update(
            current,
            power,
            dt,
            capacity,
            efficiency_charge=eta_c,
            efficiency_discharge=eta_d,
        )
        assert traj["soc"][i] == pytest.approx(step["soc"])
        assert traj["delta_soc"][i] == pytest.approx(step["delta_soc"])
        assert traj["energy_delta"][i] == pytest.approx(step["energy_delta"])
        assert traj["clipped"][i] is step["clipped"]
        current = step["soc"]

    assert traj["soc_path"] == pytest.approx([0.5, *traj["soc"]])


def test_storage_trajectory_per_step_dt_hours() -> None:
    powers = [10.0, 10.0]
    dts = [1.0, 0.5]
    traj = storage_trajectory(0.5, powers, dts, capacity=100.0)

    # Step 1: +10 Wh → SOC 0.6; step 2: +5 Wh → SOC 0.65
    assert traj["soc"][0] == pytest.approx(0.6)
    assert traj["soc"][1] == pytest.approx(0.65)
    assert traj["energy_delta"] == pytest.approx([10.0, 5.0])


def test_storage_trajectory_reports_any_clipped() -> None:
    traj = storage_trajectory(0.9, [20.0, -5.0], 1.0, capacity=100.0)
    assert traj["clipped"][0] is True
    assert traj["any_clipped"] is True
    assert traj["soc"][0] == 1.0
    # After clip to 1.0, discharge 5 Wh → 0.95
    assert traj["soc"][1] == pytest.approx(0.95)


def test_storage_trajectory_empty_powers() -> None:
    traj = storage_trajectory(0.4, [], 1.0, capacity=50.0)
    assert traj["soc_path"] == [0.4]
    assert traj["soc"] == []
    assert traj["delta_soc"] == []
    assert traj["energy_delta"] == []
    assert traj["clipped"] == []
    assert traj["any_clipped"] is False
    assert traj["soc_final"] == 0.4


def test_storage_trajectory_rejects_dt_length_mismatch() -> None:
    with pytest.raises(ValueError, match="dt_hours sequence length"):
        storage_trajectory(0.5, [1.0, 2.0], [1.0], capacity=100.0)


def test_public_api_does_not_label_power_path_as_coulomb_counting() -> None:
    """ADR 0027 / Wave 1: public physics API is energy-based, not coulomb-counting."""
    module_doc = inspect.getmodule(energy_based_soc_update).__doc__ or ""
    func_doc = (energy_based_soc_update.__doc__ or "") + (storage_trajectory.__doc__ or "")
    combined = (module_doc + "\n" + func_doc).lower()
    assert "energy-based" in combined or "energy based" in combined
    assert "coulomb" not in combined
    assert energy_based_soc_update.__name__ == "energy_based_soc_update"
