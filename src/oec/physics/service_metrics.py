"""Generic energy service metrics (v2.6.1 Wave 1).

Public EaaS-oriented **physics** metrics only:

* :func:`energy_delivered` — total load energy over a horizon
  (``Σ load · Δt``).
* :func:`autonomy_hours` — how long local resources (PV + storage energy)
  can serve the load **without the grid**.

No commercial scoring, pricing, tariffs, or time-of-use logic.
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = [
    "energy_delivered",
    "autonomy_hours",
]


def _as_float_series(name: str, values: Sequence[float], n: int | None = None) -> list[float]:
    series = [float(x) for x in values]
    if n is not None and len(series) != n:
        raise ValueError(f"{name} length ({len(series)}) must match load length ({n})")
    return series


def _as_dt_list(dt_hours: float | Sequence[float], n: int) -> list[float]:
    """Resolve scalar or per-step ``dt_hours`` to a length-``n`` list."""
    if isinstance(dt_hours, int | float) and not isinstance(dt_hours, bool):
        dt = float(dt_hours)
        if dt < 0:
            raise ValueError("dt_hours must be non-negative")
        return [dt] * n
    # bool is a subclass of int; excluded above so else is Sequence[float].
    dts = [float(x) for x in dt_hours]  # type: ignore[union-attr]
    if len(dts) != n:
        raise ValueError(f"dt_hours sequence length ({len(dts)}) must match series length ({n})")
    if any(dt < 0 for dt in dts):
        raise ValueError("dt_hours values must be non-negative")
    return dts


def energy_delivered(
    load_series: Sequence[float],
    pv_series: Sequence[float],
    storage_discharge_series: Sequence[float],
    grid_import_series: Sequence[float],
    dt_hours: float | Sequence[float],
) -> float:
    """Total energy delivered to the load over the horizon.

    Physics formula (piecewise-constant power integration)::

        E_delivered = Σ_t load[t] · Δt[t]

    Parameters
    ----------
    load_series:
        Load power at each step (same power unit throughout).
    pv_series, storage_discharge_series, grid_import_series:
        Companion service series of the same length as ``load_series``.
        They document the service composition and are length-checked for
        API consistency; they do **not** enter the delivered-energy integral
        (delivered energy is defined on the load alone).
    dt_hours:
        Scalar step duration in hours, or a per-step sequence of the same
        length as ``load_series``. Non-negative.

    Returns
    -------
    float
        Total load energy in the unit of ``power × hours``.

    Notes
    -----
    No pricing, TOU, or commercial scoring. Empty ``load_series`` yields
    ``0.0``.
    """
    load = _as_float_series("load_series", load_series)
    n = len(load)
    _as_float_series("pv_series", pv_series, n)
    _as_float_series("storage_discharge_series", storage_discharge_series, n)
    _as_float_series("grid_import_series", grid_import_series, n)
    dts = _as_dt_list(dt_hours, n)

    if n == 0:
        return 0.0

    return float(sum(p * dt for p, dt in zip(load, dts, strict=True)))


def autonomy_hours(
    load_series: Sequence[float],
    pv_series: Sequence[float],
    storage_capacity: float,
    storage_initial_soc: float,
    dt_hours: float | Sequence[float],
) -> float:
    """Hours the load can be served without the grid (PV + storage only).

    Walks the horizon islanded: each step compares load power to PV power;
    storage energy covers any local shortfall. Surplus PV recharges storage
    up to ``storage_capacity``. When storage cannot cover a full step, a
    fractional step duration is returned (energy / net deficit power).

    Parameters
    ----------
    load_series:
        Load power at each step (same power unit throughout).
    pv_series:
        PV power at each step (same power unit as ``load_series``).
    storage_capacity:
        Energy capacity (same energy unit as ``power × hours``). Must be
        non-negative.
    storage_initial_soc:
        Initial state of charge as a fraction of energy capacity in
        ``[0, 1]``.
    dt_hours:
        Scalar step duration in hours, or a per-step sequence of the same
        length as ``load_series``. Non-negative.

    Returns
    -------
    float
        Autonomy duration in hours, in ``[0, Σ Δt]``. If local resources
        cover the entire provided horizon, returns the full horizon length.
        Empty series yield ``0.0``.

    Notes
    -----
    Grid is excluded by construction (no import). No commercial scoring,
    pricing, or TOU. Efficiencies are ideal (η = 1) in this v0 helper;
    energy-based storage with η lives in :mod:`oec.physics.storage`.
    """
    capacity = float(storage_capacity)
    if capacity < 0:
        raise ValueError("storage_capacity must be non-negative")
    soc0 = float(storage_initial_soc)
    if not 0.0 <= soc0 <= 1.0:
        raise ValueError("storage_initial_soc must be in [0, 1]")

    load = _as_float_series("load_series", load_series)
    n = len(load)
    pv = _as_float_series("pv_series", pv_series, n)
    dts = _as_dt_list(dt_hours, n)

    if n == 0:
        return 0.0

    energy = capacity * soc0
    hours = 0.0

    for p_load, p_pv, dt in zip(load, pv, dts, strict=True):
        # Net power drawn from storage: positive = discharge, negative = charge.
        net = float(p_load) - float(p_pv)

        if net <= 0.0:
            # PV covers load; surplus recharges storage up to capacity.
            if dt > 0.0 and capacity > 0.0:
                surplus_energy = (-net) * dt
                headroom = capacity - energy
                energy = min(capacity, energy + min(surplus_energy, max(0.0, headroom)))
            hours += dt
            continue

        # Need storage for net * dt energy.
        if dt <= 0.0:
            # Zero-duration step: nothing further to accumulate.
            continue

        need = net * dt
        if energy + 1e-15 >= need:
            energy = max(0.0, energy - need)
            hours += dt
            continue

        # Partial step: remaining storage energy / net deficit power.
        if net > 0.0 and energy > 0.0:
            hours += energy / net
        energy = 0.0
        break

    return float(hours)
