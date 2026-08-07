"""Grid-zero feasibility helpers (v2.6.1 Wave 1).

Deterministic evaluation of a **provided** multiperiod trajectory
(load / PV / storage charge-discharge / grid import). **No** linear program,
**no** capacity minimization, **no** HiGHS — physics only.

Grid convention (same as :mod:`oec.physics.hybrid`): ``grid_import > 0`` is
import from the grid; **export is negative** ``grid_import`` (single field).

Grid-zero means **no positive import** on the horizon (export allowed). A
trajectory is feasible when the hybrid energy balance holds under the
conservation tolerance policy, every period has zero unmet-load deficit, and
there is no grid import.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from oec.physics.hybrid import hybrid_balance

__all__ = [
    "grid_zero_feasibility",
]


def _period_tolerance(atol: float, rtol: float, scale: float) -> float:
    """Shared absolute threshold ``atol + rtol * scale`` for zero tests."""
    return float(atol) + float(rtol) * float(scale)


def grid_zero_feasibility(
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
    """Evaluate grid-zero feasibility of a provided multiperiod trajectory.

    Parameters
    ----------
    load, pv, grid_import:
        Period series of equal length (same energy unit throughout).
        ``grid_import > 0`` imports; ``grid_import < 0`` exports.
    charge, discharge:
        Optional non-negative storage series. Default is zeros of length ``N``.
    atol, rtol, scale, unit:
        Passed through to :func:`oec.physics.hybrid.hybrid_balance` / the
        conservation owner for residual checks. The same
        ``atol + rtol * scale`` threshold is used for deficit and import
        zero-tests.

    Returns
    -------
    dict
        ``feasible`` — ``True`` iff balance holds, no period deficit, and no
        positive grid import (all within tolerance);
        ``deficit_per_period`` — length-``N`` unmet load if the grid import
        term were removed: ``max(0, load − (pv + discharge − charge))``;
        ``balance_residual`` — length-``N`` hybrid residuals
        ``load − (pv + grid_import + discharge − charge)``;
        ``flags`` — structured booleans (see below);
        plus echoed series, ``n``, tolerance fields, and hybrid ``balance`` /
        ``period_checks`` for audit.

    Notes
    -----
    Deficit is defined against **local** supply (PV + storage net), not against
    the hybrid residual after grid. When the trajectory is balanced,
    ``deficit_per_period[t] == max(0, grid_import[t])`` (import equals the
    local shortfall). This module never solves for dispatch or capacity.
    """
    hybrid = hybrid_balance(
        load,
        pv,
        grid_import,
        charge=charge,
        discharge=discharge,
        atol=atol,
        rtol=rtol,
        scale=scale,
        unit=unit,
    )

    n = int(hybrid["n"])
    load_list: list[float] = hybrid["load"]
    pv_list: list[float] = hybrid["pv"]
    grid_list: list[float] = hybrid["grid_import"]
    charge_list: list[float] = hybrid["charge"]
    discharge_list: list[float] = hybrid["discharge"]
    balance_residual: list[float] = list(hybrid["residuals"])
    used_scale = float(hybrid["scale"])
    used_atol = float(hybrid["atol"])
    used_rtol = float(hybrid["rtol"])
    tol = _period_tolerance(used_atol, used_rtol, used_scale)

    deficit_per_period: list[float] = []
    for t in range(n):
        local_supply = pv_list[t] + discharge_list[t] - charge_list[t]
        local_shortfall = load_list[t] - local_supply
        deficit_per_period.append(max(0.0, float(local_shortfall)))

    period_has_deficit = [d > tol for d in deficit_per_period]
    period_has_import = [g > tol for g in grid_list]
    period_has_export = [g < -tol for g in grid_list]
    period_balanced = [bool(hybrid["period_checks"][f"t{t}"].balanced) for t in range(n)]

    has_deficit = any(period_has_deficit)
    has_grid_import = any(period_has_import)
    has_grid_export = any(period_has_export)
    balance_ok = bool(hybrid["balanced"])
    # Grid-zero: no positive import on the horizon (export allowed).
    grid_zero = not has_grid_import
    feasible = balance_ok and not has_deficit and grid_zero

    flags: dict[str, Any] = {
        "balance_ok": balance_ok,
        "has_deficit": has_deficit,
        "has_grid_import": has_grid_import,
        "has_grid_export": has_grid_export,
        "grid_zero": grid_zero,
        "period_has_deficit": period_has_deficit,
        "period_has_import": period_has_import,
        "period_has_export": period_has_export,
        "period_balanced": period_balanced,
    }

    return {
        "feasible": feasible,
        "deficit_per_period": deficit_per_period,
        "balance_residual": balance_residual,
        "flags": flags,
        "n": n,
        "load": load_list,
        "pv": pv_list,
        "grid_import": grid_list,
        "charge": charge_list,
        "discharge": discharge_list,
        "period_checks": dict(hybrid["period_checks"]),
        "balance": hybrid["balance"],
        "unit": hybrid["unit"],
        "atol": used_atol,
        "rtol": used_rtol,
        "scale": used_scale,
        "tolerance": tol,
    }
