"""Multi-period hybrid energy balance (v2.6.1 Wave 1).

Canonical public API for the hybrid residual over a provided trajectory:

    LOAD[t] = PV[t] + grid_import[t] + discharge[t] − charge[t]

**Grid convention (single field):** ``grid_import > 0`` is import from the
grid; **export is represented as a negative** ``grid_import`` (there is no
separate ``grid_export`` field). Storage charge and discharge are separate
non-negative series (aligned with the public multiperiod LP textbook form).

Per-period residuals are checked through the conservation owner
(:mod:`oec.physics.conservation`) so the tolerance formula is never
reimplemented here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from oec.physics.conservation import aggregate_balance, evaluate_vector_residual
from oec.physics.result import ConservationCheck

__all__ = [
    "hybrid_balance",
    "hybrid_period_residual",
]


def hybrid_period_residual(
    load: float,
    pv: float,
    grid_import: float,
    charge: float,
    discharge: float,
) -> float:
    """Scalar hybrid residual for one period.

    Returns
    -------
    float
        ``load − (pv + grid_import + discharge − charge)``. Zero when the
        balance holds. ``grid_import < 0`` means export (single-field
        convention).
    """
    return float(load) - (float(pv) + float(grid_import) + float(discharge) - float(charge))


def _as_float_series(name: str, values: Sequence[float], n: int) -> list[float]:
    series = [float(x) for x in values]
    if len(series) != n:
        raise ValueError(f"{name} length ({len(series)}) must match load length ({n})")
    return series


def _default_scale(
    load: Sequence[float],
    pv: Sequence[float],
    grid_import: Sequence[float],
    charge: Sequence[float],
    discharge: Sequence[float],
) -> float:
    """Shared magnitude scale for the vector residual tolerance policy."""
    magnitudes = [abs(float(x)) for x in load]
    magnitudes.extend(abs(float(x)) for x in pv)
    magnitudes.extend(abs(float(x)) for x in grid_import)
    magnitudes.extend(abs(float(x)) for x in charge)
    magnitudes.extend(abs(float(x)) for x in discharge)
    if not magnitudes:
        return 1.0
    return max(1.0, max(magnitudes))


def hybrid_balance(
    load: Sequence[float],
    pv: Sequence[float],
    grid_import: Sequence[float],
    *,
    charge: Sequence[float] | None = None,
    discharge: Sequence[float] | None = None,
    atol: float = 1e-6,
    rtol: float = 1e-9,
    scale: float | None = None,
    unit: str = "MWh",
) -> dict[str, Any]:
    """Multi-period hybrid balance with conservation-owned residual checks.

    Parameters
    ----------
    load, pv, grid_import:
        Period series of equal length (same energy unit throughout, e.g. MWh
        per period). ``grid_import > 0`` imports; **``grid_import < 0`` exports**
        (single field — do not pass a separate export series).
    charge, discharge:
        Optional non-negative storage series. Default is zeros of length ``N``.
        Simultaneous charge and discharge is allowed numerically (no
        complementarity enforced here); optimization skills may tighten that.
    atol, rtol, scale:
        Tolerance policy for :func:`oec.physics.conservation.evaluate_residual`
        (``abs(r) <= atol + rtol * scale``). When ``scale`` is omitted, a
        shared scale is derived from the max absolute term on the horizon
        (at least ``1.0``).
    unit:
        Residual unit label reported on each :class:`ConservationCheck`
        (caller-owned; default ``"MWh"`` for the public 6-period fixture).

    Returns
    -------
    dict
        ``n`` — horizon length;
        ``residuals`` — length-``N`` raw residuals;
        ``supply`` — length-``N`` right-hand side
        ``pv + grid_import + discharge − charge``;
        ``period_checks`` — mapping ``"t0"``…``"t{N-1}"`` →
        :class:`ConservationCheck` from the conservation owner;
        ``balance`` — aggregate :class:`ConservationCheck` via
        :func:`~oec.physics.conservation.aggregate_balance`;
        ``balanced`` — ``True`` iff every period and the aggregate pass;
        ``load``, ``pv``, ``grid_import``, ``charge``, ``discharge`` — echoed
        float series;
        ``unit``, ``atol``, ``rtol``, ``scale`` — policy used.

    Notes
    -----
    Curtailable PV is out of scope for v0: the full ``pv`` series enters the
    residual. Storage SOC dynamics are not integrated here — pass an already
    consistent charge/discharge schedule (see :mod:`oec.physics.storage`).
    """
    load_list = [float(x) for x in load]
    n = len(load_list)
    if n == 0:
        raise ValueError("load series must be non-empty")

    pv_list = _as_float_series("pv", pv, n)
    grid_list = _as_float_series("grid_import", grid_import, n)

    charge_list = [0.0] * n if charge is None else _as_float_series("charge", charge, n)
    discharge_list = [0.0] * n if discharge is None else _as_float_series("discharge", discharge, n)

    if any(c < 0 for c in charge_list):
        raise ValueError("charge values must be non-negative")
    if any(d < 0 for d in discharge_list):
        raise ValueError("discharge values must be non-negative")
    if any(p < 0 for p in pv_list):
        raise ValueError("pv values must be non-negative")
    if any(ld < 0 for ld in load_list):
        raise ValueError("load values must be non-negative")

    residuals: list[float] = []
    supply: list[float] = []
    residual_map: dict[str, float] = {}
    for t in range(n):
        s = pv_list[t] + grid_list[t] + discharge_list[t] - charge_list[t]
        r = hybrid_period_residual(
            load_list[t],
            pv_list[t],
            grid_list[t],
            charge_list[t],
            discharge_list[t],
        )
        supply.append(s)
        residuals.append(r)
        residual_map[f"t{t}"] = r

    used_scale = (
        float(scale)
        if scale is not None
        else _default_scale(load_list, pv_list, grid_list, charge_list, discharge_list)
    )

    period_checks: Mapping[str, ConservationCheck] = evaluate_vector_residual(
        residual_map,
        atol=atol,
        rtol=rtol,
        scale=used_scale,
        unit=unit,
    )
    balance = aggregate_balance(period_checks)

    return {
        "n": n,
        "residuals": residuals,
        "supply": supply,
        "period_checks": dict(period_checks),
        "balance": balance,
        "balanced": bool(balance.balanced),
        "load": load_list,
        "pv": pv_list,
        "grid_import": grid_list,
        "charge": charge_list,
        "discharge": discharge_list,
        "unit": unit,
        "atol": float(atol),
        "rtol": float(rtol),
        "scale": used_scale,
    }
