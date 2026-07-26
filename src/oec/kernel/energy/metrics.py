"""Generic energy metrics — no proprietary dispatch or BTM methodology."""

from __future__ import annotations

from typing import Any


def energy_balance(
    energy_in: list[float],
    energy_out: list[float],
    *,
    storage_delta: float = 0.0,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Check ΣE_in = ΣE_out + Δstorage (same energy unit for all terms)."""
    if len(energy_in) == 0 and len(energy_out) == 0:
        raise ValueError("energy_in and energy_out cannot both be empty")
    total_in = float(sum(energy_in))
    total_out = float(sum(energy_out))
    residual = total_in - total_out - float(storage_delta)
    balanced = abs(residual) <= float(tolerance)
    return {
        "total_in": total_in,
        "total_out": total_out,
        "storage_delta": float(storage_delta),
        "residual": residual,
        "balanced": balanced,
        "tolerance": float(tolerance),
    }


def soc_update(
    soc: float,
    power: float,
    dt_hours: float,
    capacity: float,
    *,
    efficiency_charge: float = 1.0,
    efficiency_discharge: float = 1.0,
) -> dict[str, Any]:
    """Coulomb-counting SOC step (generic).

    power > 0 charges the storage; power < 0 discharges.
    SOC returned in [0, 1] fraction of capacity (same power*time unit as capacity).
    """
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    if not 0 <= soc <= 1:
        raise ValueError("soc must be in [0, 1]")
    if dt_hours < 0:
        raise ValueError("dt_hours must be non-negative")
    if not 0 < efficiency_charge <= 1 or not 0 < efficiency_discharge <= 1:
        raise ValueError("efficiencies must be in (0, 1]")

    if power >= 0:
        delta_e = power * dt_hours * efficiency_charge
    else:
        delta_e = power * dt_hours / efficiency_discharge

    delta_soc = delta_e / capacity
    soc_next = soc + delta_soc
    clipped = soc_next < 0.0 or soc_next > 1.0
    soc_next = min(1.0, max(0.0, soc_next))
    return {
        "soc": float(soc_next),
        "delta_soc": float(delta_soc),
        "clipped": bool(clipped),
        "energy_delta": float(delta_e),
    }


def load_metrics(power_values: list[float]) -> dict[str, Any]:
    """Peak, average, load factor for a power series (same unit throughout)."""
    if not power_values:
        raise ValueError("power_values must be non-empty")
    peak = float(max(power_values))
    average = float(sum(power_values) / len(power_values))
    load_factor = None if peak == 0.0 else float(average / peak)
    return {
        "n": len(power_values),
        "peak": peak,
        "average": average,
        "load_factor": load_factor,
        "min": float(min(power_values)),
    }
