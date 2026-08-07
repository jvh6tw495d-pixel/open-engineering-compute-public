"""Generic photovoltaic (PV) model v0 (v2.6.1 Wave 1).

Canonical public API for a **generic** PV generator:

* Instantaneous power: ``P = G × A × η`` with optional linear temperature
  correction of power/efficiency.
* Energy from a power series (pre-computed **or** derived from irradiance)
  via piecewise-constant integration ``E = Σ P_i · Δt_i``.

v0 intentionally omits incidence-angle modifiers, spectral mismatch, soiling,
shading, and inverter clipping — those are future extensions.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from oec.core.types import Assumption

__all__ = [
    "PV_ASSUMPTIONS",
    "pv_energy_from_series",
    "pv_power",
]

PV_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(
        text="Plane-of-array irradiance G is the effective irradiance on the array plane",
        source="PV v0",
    ),
    Assumption(
        text="Constant array area A and efficiency η at the reference temperature",
        source="PV v0",
    ),
    Assumption(
        text=(
            "Linear temperature correction of power when γ and T are supplied: "
            "P = G · A · η · (1 + γ · (T − T_ref))"
        ),
        source="PV v0",
    ),
    Assumption(
        text=(
            "No incidence-angle modifier, spectral mismatch, soiling, shading, "
            "or inverter clipping in v0"
        ),
        source="PV v0",
    ),
    Assumption(
        text=(
            "Energy from a power series uses piecewise-constant (rectangular) "
            "integration E = Σ P_i · Δt_i"
        ),
        source="PV v0",
    ),
)

_DEFAULT_REFERENCE_TEMPERATURE_C = 25.0


def _temperature_factor(
    temperature: float | None,
    temperature_coefficient: float | None,
    reference_temperature: float,
) -> float:
    """Return ``1 + γ · (T − T_ref)`` when both T and γ are set; else ``1.0``."""
    if temperature is None and temperature_coefficient is None:
        return 1.0
    if temperature is None or temperature_coefficient is None:
        raise ValueError(
            "temperature and temperature_coefficient must both be provided "
            "for temperature correction, or both omitted"
        )
    return 1.0 + float(temperature_coefficient) * (
        float(temperature) - float(reference_temperature)
    )


def _validate_scalar_geometry(irradiance: float, area: float, efficiency: float) -> None:
    if irradiance < 0:
        raise ValueError("irradiance must be non-negative")
    if area <= 0:
        raise ValueError("area must be positive")
    if not 0 < efficiency <= 1:
        raise ValueError("efficiency must be in (0, 1]")


def pv_power(
    irradiance: float,
    area: float,
    efficiency: float,
    *,
    temperature: float | None = None,
    temperature_coefficient: float | None = None,
    reference_temperature: float = _DEFAULT_REFERENCE_TEMPERATURE_C,
) -> dict[str, Any]:
    """Instantaneous PV power: ``P = G × A × η × f_temp``.

    Parameters
    ----------
    irradiance:
        Plane-of-array irradiance ``G`` (power per area; e.g. W/m²).
    area:
        Array / module active area ``A`` (same area unit as in ``G``).
    efficiency:
        Conversion efficiency ``η`` at the reference temperature, in ``(0, 1]``.
    temperature:
        Cell or module temperature ``T`` (same scale as
        ``reference_temperature``, typically °C). Optional; requires
        ``temperature_coefficient`` when set.
    temperature_coefficient:
        Linear temperature coefficient of power ``γ`` (1/temperature unit).
        Optional; requires ``temperature`` when set. Typical crystalline-Si
        values are negative (e.g. ``-0.004`` / °C).
    reference_temperature:
        Reference temperature ``T_ref`` for the linear correction (default
        ``25.0``, STC).

    Returns
    -------
    dict
        ``power`` — DC electrical power in the unit of ``G × A``;
        ``temperature_factor`` — ``f_temp = 1 + γ·(T − T_ref)`` (or ``1.0``);
        ``efficiency_effective`` — ``η × f_temp``;
        ``irradiance``, ``area``, ``efficiency`` — echoed inputs as floats.

    Notes
    -----
    Hypotheses are listed in :data:`PV_ASSUMPTIONS`. When temperature
    correction is omitted, ``f_temp = 1`` and the model reduces to
    ``P = G × A × η``.
    """
    g = float(irradiance)
    a = float(area)
    eta = float(efficiency)
    _validate_scalar_geometry(g, a, eta)

    f_temp = _temperature_factor(
        temperature,
        temperature_coefficient,
        reference_temperature,
    )
    eta_eff = eta * f_temp
    power = g * a * eta_eff

    return {
        "power": float(power),
        "temperature_factor": float(f_temp),
        "efficiency_effective": float(eta_eff),
        "irradiance": g,
        "area": a,
        "efficiency": eta,
    }


def _as_dt_list(dt_hours: float | Sequence[float], n: int) -> list[float]:
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


def pv_energy_from_series(
    powers: Sequence[float] | None = None,
    dt_hours: float | Sequence[float] = 1.0,
    *,
    irradiance: Sequence[float] | None = None,
    area: float | None = None,
    efficiency: float | None = None,
    temperatures: float | Sequence[float] | None = None,
    temperature_coefficient: float | None = None,
    reference_temperature: float = _DEFAULT_REFERENCE_TEMPERATURE_C,
) -> dict[str, Any]:
    """Integrate a PV power series to energy (piecewise-constant).

    Two mutually exclusive input modes:

    1. **Pre-computed power** — pass ``powers`` (and optional ``dt_hours``).
    2. **Irradiance path** — pass ``irradiance``, ``area``, and ``efficiency``;
       each step is converted with :func:`pv_power` (optional per-step or
       scalar temperature correction).

    Energy uses rectangular integration consistent with energy-based storage
    steps: ``E_i = P_i · Δt_i``, ``E_total = Σ E_i``.

    Parameters
    ----------
    powers:
        Pre-computed PV power at each step (same power unit throughout).
        Mutually exclusive with the irradiance path.
    dt_hours:
        Scalar duration applied to every step, or a per-step sequence of the
        same length as the power/irradiance series. Non-negative hours.
    irradiance:
        Plane-of-array irradiance series (irradiance path).
    area, efficiency:
        Constant geometry/efficiency for the irradiance path.
    temperatures:
        Optional scalar temperature or per-step series for temperature
        correction (irradiance path only; requires ``temperature_coefficient``).
    temperature_coefficient, reference_temperature:
        Same meaning as in :func:`pv_power` (irradiance path).

    Returns
    -------
    dict
        ``power`` — resolved power series (length ``N``);
        ``interval_energy`` — ``P_i · Δt_i`` (length ``N``);
        ``total_energy`` — sum of interval energies;
        ``dt_hours`` — resolved durations (length ``N``);
        ``n`` — number of steps;
        ``temperature_factor`` — per-step factors when the irradiance path is
        used (length ``N``); omitted for pre-computed power.
    """
    if powers is not None and irradiance is not None:
        raise ValueError("provide either powers or irradiance, not both")
    if powers is None and irradiance is None:
        raise ValueError("provide either powers or irradiance series")

    if powers is not None:
        if area is not None or efficiency is not None:
            raise ValueError(
                "area and efficiency apply only to the irradiance path, not pre-computed powers"
            )
        if temperatures is not None or temperature_coefficient is not None:
            raise ValueError(
                "temperature correction applies only to the irradiance path; "
                "pass powers already corrected, or use irradiance + area + efficiency"
            )
        power_list = [float(p) for p in powers]
        n = len(power_list)
        dts = _as_dt_list(dt_hours, n)
        interval_energy = [p * dt for p, dt in zip(power_list, dts, strict=True)]
        return {
            "power": power_list,
            "interval_energy": interval_energy,
            "total_energy": float(sum(interval_energy)),
            "dt_hours": dts,
            "n": n,
        }

    # Irradiance path (powers is None; irradiance is not None)
    if irradiance is None:
        raise ValueError("provide either powers or irradiance series")
    if area is None or efficiency is None:
        raise ValueError("irradiance path requires area and efficiency")

    irr = [float(g) for g in irradiance]
    n = len(irr)
    dts = _as_dt_list(dt_hours, n)

    if temperatures is None:
        temp_list: list[float | None] = [None] * n
    elif isinstance(temperatures, int | float) and not isinstance(temperatures, bool):
        temp_list = [float(temperatures)] * n
    else:
        # bool excluded above; remaining union member is Sequence[float].
        temp_list = [float(t) for t in temperatures]  # type: ignore[union-attr]
        if len(temp_list) != n:
            raise ValueError(
                f"temperatures sequence length ({len(temp_list)}) must match "
                f"irradiance length ({n})"
            )

    power_list = []
    factors: list[float] = []
    for g, t in zip(irr, temp_list, strict=True):
        step = pv_power(
            g,
            float(area),
            float(efficiency),
            temperature=t,
            temperature_coefficient=temperature_coefficient,
            reference_temperature=reference_temperature,
        )
        power_list.append(float(step["power"]))
        factors.append(float(step["temperature_factor"]))

    interval_energy = [p * dt for p, dt in zip(power_list, dts, strict=True)]
    return {
        "power": power_list,
        "interval_energy": interval_energy,
        "total_energy": float(sum(interval_energy)),
        "dt_hours": dts,
        "n": n,
        "temperature_factor": factors,
    }
