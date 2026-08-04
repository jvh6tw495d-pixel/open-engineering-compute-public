"""Unit tests for generic energy service metrics (v2.6.1 Wave 1 step 1.6)."""

from __future__ import annotations

import pytest

from oec.physics.service_metrics import autonomy_hours, energy_delivered

# ---------------------------------------------------------------------------
# energy_delivered
# ---------------------------------------------------------------------------


def test_energy_delivered_sum_load_times_dt() -> None:
    """E = Σ load · Δt for scalar dt (explicit physics formula)."""
    load = [10.0, 20.0, 5.0]
    # Companion series length-checked only (do not enter the integral).
    pv = [1.0, 2.0, 0.0]
    discharge = [0.0, 5.0, 0.0]
    grid = [9.0, 13.0, 5.0]
    dt = 1.0

    out = energy_delivered(load, pv, discharge, grid, dt)
    assert out == pytest.approx(35.0)


def test_energy_delivered_per_step_dt() -> None:
    load = [10.0, 20.0]
    zeros = [0.0, 0.0]
    out = energy_delivered(load, zeros, zeros, zeros, dt_hours=[1.0, 0.5])
    # 10*1 + 20*0.5 = 20
    assert out == pytest.approx(20.0)


def test_energy_delivered_empty_series() -> None:
    assert energy_delivered([], [], [], [], dt_hours=1.0) == 0.0


def test_energy_delivered_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="pv_series length"):
        energy_delivered([1.0, 2.0], [1.0], [0.0, 0.0], [0.0, 0.0], 1.0)
    with pytest.raises(ValueError, match="storage_discharge_series length"):
        energy_delivered([1.0], [0.0], [0.0, 0.0], [0.0], 1.0)
    with pytest.raises(ValueError, match="grid_import_series length"):
        energy_delivered([1.0], [0.0], [0.0], [0.0, 1.0], 1.0)
    with pytest.raises(ValueError, match="dt_hours sequence length"):
        energy_delivered([1.0, 2.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [1.0])


def test_energy_delivered_rejects_negative_dt() -> None:
    with pytest.raises(ValueError, match="dt_hours must be non-negative"):
        energy_delivered([1.0], [0.0], [0.0], [0.0], -1.0)


def test_energy_delivered_independent_of_sources() -> None:
    """Companion PV/discharge/grid series do not change delivered energy."""
    load = [4.0, 6.0]
    dt = 2.0
    a = energy_delivered(load, [0.0, 0.0], [0.0, 0.0], [4.0, 6.0], dt)
    b = energy_delivered(load, [100.0, 100.0], [50.0, 50.0], [-10.0, 0.0], dt)
    assert a == pytest.approx(20.0)
    assert b == pytest.approx(20.0)
    assert a == pytest.approx(b)


# ---------------------------------------------------------------------------
# autonomy_hours
# ---------------------------------------------------------------------------


def test_autonomy_hours_storage_only_covers_full_horizon() -> None:
    """Constant 10 kW load, no PV, 50 kWh at SOC 1.0, dt=1 → 5 h full cover."""
    load = [10.0, 10.0, 10.0, 10.0, 10.0]
    pv = [0.0] * 5
    hours = autonomy_hours(load, pv, storage_capacity=50.0, storage_initial_soc=1.0, dt_hours=1.0)
    assert hours == pytest.approx(5.0)


def test_autonomy_hours_storage_only_partial_last_step() -> None:
    """30 kWh at full SOC vs 10 kW load → 3.0 h (exactly 3 full steps)."""
    load = [10.0] * 5
    pv = [0.0] * 5
    hours = autonomy_hours(load, pv, storage_capacity=30.0, storage_initial_soc=1.0, dt_hours=1.0)
    assert hours == pytest.approx(3.0)


def test_autonomy_hours_fractional_step() -> None:
    """25 kWh vs 10 kW load → 2.5 h (two full steps + half of third)."""
    load = [10.0, 10.0, 10.0, 10.0]
    pv = [0.0] * 4
    hours = autonomy_hours(load, pv, storage_capacity=25.0, storage_initial_soc=1.0, dt_hours=1.0)
    assert hours == pytest.approx(2.5)


def test_autonomy_hours_pv_covers_load_no_storage_draw() -> None:
    """PV equals load every step → full horizon even with empty storage."""
    load = [5.0, 5.0, 5.0]
    pv = [5.0, 5.0, 5.0]
    hours = autonomy_hours(load, pv, storage_capacity=0.0, storage_initial_soc=0.0, dt_hours=1.0)
    assert hours == pytest.approx(3.0)


def test_autonomy_hours_pv_reduces_storage_draw() -> None:
    """Load 10, PV 4 → net 6 kW; 12 kWh storage → 2.0 h."""
    load = [10.0, 10.0, 10.0]
    pv = [4.0, 4.0, 4.0]
    hours = autonomy_hours(load, pv, storage_capacity=12.0, storage_initial_soc=1.0, dt_hours=1.0)
    assert hours == pytest.approx(2.0)


def test_autonomy_hours_surplus_pv_recharges_storage() -> None:
    """Step 0: PV surplus charges storage; later deficit uses recharged energy.

    Horizon: load=[0, 10], pv=[10, 0], capacity=5, soc0=0, dt=1
    - t0: net = -10 → charge 5 kWh (headroom), hours=1
    - t1: net = 10 → need 10, have 5 → +0.5 h → total 1.5 h
    """
    hours = autonomy_hours(
        load_series=[0.0, 10.0],
        pv_series=[10.0, 0.0],
        storage_capacity=5.0,
        storage_initial_soc=0.0,
        dt_hours=1.0,
    )
    assert hours == pytest.approx(1.5)


def test_autonomy_hours_zero_when_empty_and_deficit() -> None:
    """No PV, empty storage, positive load → 0 h autonomy."""
    hours = autonomy_hours(
        load_series=[5.0, 5.0],
        pv_series=[0.0, 0.0],
        storage_capacity=10.0,
        storage_initial_soc=0.0,
        dt_hours=1.0,
    )
    assert hours == pytest.approx(0.0)


def test_autonomy_hours_initial_soc_fraction() -> None:
    """capacity 100, soc 0.2 → 20 kWh available; load 10 → 2 h."""
    hours = autonomy_hours(
        load_series=[10.0] * 5,
        pv_series=[0.0] * 5,
        storage_capacity=100.0,
        storage_initial_soc=0.2,
        dt_hours=1.0,
    )
    assert hours == pytest.approx(2.0)


def test_autonomy_hours_empty_series() -> None:
    assert (
        autonomy_hours([], [], storage_capacity=10.0, storage_initial_soc=1.0, dt_hours=1.0) == 0.0
    )


def test_autonomy_hours_rejects_invalid_capacity_and_soc() -> None:
    with pytest.raises(ValueError, match="storage_capacity must be non-negative"):
        autonomy_hours([1.0], [0.0], storage_capacity=-1.0, storage_initial_soc=0.5, dt_hours=1.0)
    with pytest.raises(ValueError, match="storage_initial_soc must be in"):
        autonomy_hours([1.0], [0.0], storage_capacity=10.0, storage_initial_soc=1.5, dt_hours=1.0)
    with pytest.raises(ValueError, match="storage_initial_soc must be in"):
        autonomy_hours([1.0], [0.0], storage_capacity=10.0, storage_initial_soc=-0.1, dt_hours=1.0)


def test_autonomy_hours_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="pv_series length"):
        autonomy_hours([1.0, 2.0], [0.0], 10.0, 1.0, 1.0)


def test_autonomy_hours_no_commercial_fields() -> None:
    """Return type is a bare float — no price, score, or TOU payload."""
    out = autonomy_hours([1.0], [0.0], 10.0, 1.0, 1.0)
    assert isinstance(out, float)
    # energy_delivered likewise
    e = energy_delivered([1.0], [0.0], [0.0], [0.0], 1.0)
    assert isinstance(e, float)
