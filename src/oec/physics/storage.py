"""Energy-based BESS storage SOC dynamics (v2.6.1 Wave 1).

Canonical public API for storage state-of-charge uses **energy-based**
integration: ΔSOC from power × time × η / energy capacity. Positive power
charges; negative power discharges. SOC is a fraction of energy capacity in
``[0, 1]``.

This module wraps :func:`oec.kernel.energy.metrics.soc_update` for numerical
parity and adds multi-step :func:`storage_trajectory`. Current/Ah paths are
intentionally out of scope here (reserved for a future explicit-current API).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from oec.kernel.energy.metrics import soc_update as _kernel_soc_update

__all__ = [
    "energy_based_soc_update",
    "storage_trajectory",
]


def energy_based_soc_update(
    soc: float,
    power: float,
    dt_hours: float,
    capacity: float,
    *,
    efficiency_charge: float = 1.0,
    efficiency_discharge: float = 1.0,
) -> dict[str, Any]:
    """Single-step energy-based SOC update (power × time × η / capacity).

    Parameters
    ----------
    soc:
        Initial state of charge as a fraction of energy capacity in ``[0, 1]``.
    power:
        Storage power in the same power unit implied by ``capacity / hours``.
        ``power > 0`` charges; ``power < 0`` discharges.
    dt_hours:
        Step duration in hours (non-negative).
    capacity:
        Energy capacity (same energy unit as ``power * hours``).
    efficiency_charge:
        Charge efficiency η_c ∈ (0, 1].
    efficiency_discharge:
        Discharge efficiency η_d ∈ (0, 1].

    Returns
    -------
    dict
        Keys ``soc``, ``delta_soc``, ``clipped``, ``energy_delta`` — same
        shape and values as :func:`oec.kernel.energy.metrics.soc_update` for
        identical inputs (parity).

    Notes
    -----
    Integration is energy-based (power × time / energy capacity), not a
    current/Ah path. The returned SOC is clipped to ``[0, 1]``; ``clipped``
    is ``True`` when the unconstrained step would leave that interval.
    """
    return _kernel_soc_update(
        soc,
        power,
        dt_hours,
        capacity,
        efficiency_charge=efficiency_charge,
        efficiency_discharge=efficiency_discharge,
    )


def storage_trajectory(
    soc: float,
    powers: Sequence[float],
    dt_hours: float | Sequence[float],
    capacity: float,
    *,
    efficiency_charge: float = 1.0,
    efficiency_discharge: float = 1.0,
) -> dict[str, Any]:
    """Multi-step energy-based SOC trajectory for a BESS power schedule.

    Applies :func:`energy_based_soc_update` sequentially. Each step uses the
    SOC after the previous step (with clip to ``[0, 1]``).

    Parameters
    ----------
    soc:
        Initial SOC in ``[0, 1]``.
    powers:
        Power at each step (same convention as :func:`energy_based_soc_update`).
    dt_hours:
        Scalar duration applied to every step, or a per-step sequence of the
        same length as ``powers``.
    capacity:
        Energy capacity (constant over the trajectory).
    efficiency_charge, efficiency_discharge:
        Constant charge/discharge efficiencies for the horizon.

    Returns
    -------
    dict
        ``soc_path`` — length ``N + 1`` (initial + after each step);
        ``soc`` — length ``N`` (SOC after each step);
        ``delta_soc``, ``energy_delta``, ``clipped`` — length ``N``;
        ``any_clipped`` — ``True`` if any step clipped;
        ``soc_final`` — last SOC (equals ``soc`` when ``N == 0`` then initial).
    """
    n = len(powers)
    if isinstance(dt_hours, int | float) and not isinstance(dt_hours, bool):
        dts = [float(dt_hours)] * n
    else:
        # bool is a subclass of int; excluded above so else is Sequence[float].
        dts = [float(dt) for dt in dt_hours]  # type: ignore[union-attr]
        if len(dts) != n:
            raise ValueError(
                f"dt_hours sequence length ({len(dts)}) must match powers length ({n})"
            )

    soc_path: list[float] = [float(soc)]
    delta_socs: list[float] = []
    energy_deltas: list[float] = []
    clipped_flags: list[bool] = []

    current = float(soc)
    for power, dt in zip(powers, dts, strict=True):
        step = energy_based_soc_update(
            current,
            float(power),
            dt,
            capacity,
            efficiency_charge=efficiency_charge,
            efficiency_discharge=efficiency_discharge,
        )
        current = float(step["soc"])
        soc_path.append(current)
        delta_socs.append(float(step["delta_soc"]))
        energy_deltas.append(float(step["energy_delta"]))
        clipped_flags.append(bool(step["clipped"]))

    return {
        "soc_path": soc_path,
        "soc": soc_path[1:],
        "delta_soc": delta_socs,
        "energy_delta": energy_deltas,
        "clipped": clipped_flags,
        "any_clipped": any(clipped_flags),
        "soc_final": current,
    }
