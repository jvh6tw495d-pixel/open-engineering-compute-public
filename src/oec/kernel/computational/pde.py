"""1D PDE foundations (FDM) — heat / Poisson. Merit: classical FDM; OEC governs."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from oec.errors import NumericalDomainError

PdeMode = Literal["steady", "transient"]


def heat_1d(
    *,
    length: float = 1.0,
    n_intervals: int = 20,
    left_value: float = 0.0,
    right_value: float = 0.0,
    source: float = 0.0,
    diffusivity: float = 1.0,
    mode: str = "steady",
    n_steps: int = 50,
    dt: float | None = None,
    initial: list[float] | None = None,
) -> dict[str, Any]:
    """Solve 1D heat / Poisson on [0, L] with Dirichlet boundaries.

    **steady** — solve ``-u''(x) = source`` (constant source) via second-order
    FDM. Equivalent to steady heat with uniform generation / diffusivity=1
    scaling (source absorbs k).

    **transient** — explicit FTCS for ``u_t = α u_xx + source`` with CFL
    constraint ``r = α dt / dx² ≤ 0.5``.

    Returns grid ``x``, solution ``u``, and diagnostics (no physical units;
    skill layer may wrap later).
    """
    if length <= 0:
        raise NumericalDomainError("length must be > 0", details={"length": length})
    if n_intervals < 2:
        raise NumericalDomainError("n_intervals must be >= 2", details={"n_intervals": n_intervals})
    if diffusivity <= 0:
        raise NumericalDomainError("diffusivity must be > 0", details={"diffusivity": diffusivity})

    mode_l = str(mode).lower()
    if mode_l not in {"steady", "transient"}:
        raise NumericalDomainError(
            f"unknown mode {mode!r}; allowed: ['steady', 'transient']",
            details={"mode": mode},
        )

    n = int(n_intervals)
    dx = float(length) / n
    x = np.linspace(0.0, float(length), n + 1)

    if mode_l == "steady":
        # Interior points 1..n-1: tridiagonal -u_{i-1} + 2 u_i - u_{i+1} = source * dx^2
        m = n - 1
        if m < 1:
            raise NumericalDomainError("need at least one interior point")
        a = np.zeros((m, m), dtype=float)
        b = np.full(m, float(source) * dx * dx, dtype=float)
        for i in range(m):
            a[i, i] = 2.0
            if i > 0:
                a[i, i - 1] = -1.0
            if i < m - 1:
                a[i, i + 1] = -1.0
        # Boundary contributions
        b[0] += float(left_value)
        b[-1] += float(right_value)
        u_int = np.linalg.solve(a, b)
        u = np.empty(n + 1, dtype=float)
        u[0] = float(left_value)
        u[-1] = float(right_value)
        u[1:-1] = u_int
        residual = float(np.max(np.abs(a @ u_int - b))) if m else 0.0
        return {
            "mode": "steady",
            "x": [float(v) for v in x],
            "u": [float(v) for v in u],
            "dx": dx,
            "n_intervals": n,
            "source": float(source),
            "left_value": float(left_value),
            "right_value": float(right_value),
            "diagnostics": {
                "method": "fdm_second_order_dirichlet",
                "backend": "numpy",
                "max_residual": residual,
                "converged": True,
            },
        }

    # transient explicit FTCS
    if n_steps < 1:
        raise NumericalDomainError("n_steps must be >= 1", details={"n_steps": n_steps})
    if dt is None:
        # r = 0.4 for safety margin under CFL 0.5
        dt = 0.4 * dx * dx / float(diffusivity)
    dt = float(dt)
    if dt <= 0:
        raise NumericalDomainError("dt must be > 0", details={"dt": dt})
    r = float(diffusivity) * dt / (dx * dx)
    if r > 0.5 + 1e-12:
        raise NumericalDomainError(
            f"CFL violated: r = alpha*dt/dx^2 = {r:.6g} > 0.5; reduce dt",
            details={"r": r, "dt": dt, "dx": dx, "diffusivity": diffusivity},
        )

    if initial is None:
        u = np.linspace(float(left_value), float(right_value), n + 1)
    else:
        u = np.asarray(initial, dtype=float)
        if u.shape != (n + 1,):
            raise NumericalDomainError(
                f"initial must have length n_intervals+1 = {n + 1}, got {u.size}",
                details={"expected": n + 1, "got": int(u.size)},
            )
    u = u.copy()
    u[0] = float(left_value)
    u[-1] = float(right_value)

    for _ in range(int(n_steps)):
        u_new = u.copy()
        u_new[1:-1] = u[1:-1] + r * (u[2:] - 2.0 * u[1:-1] + u[:-2]) + dt * float(source)
        u_new[0] = float(left_value)
        u_new[-1] = float(right_value)
        u = u_new

    return {
        "mode": "transient",
        "x": [float(v) for v in x],
        "u": [float(v) for v in u],
        "dx": dx,
        "dt": dt,
        "n_intervals": n,
        "n_steps": int(n_steps),
        "diffusivity": float(diffusivity),
        "source": float(source),
        "left_value": float(left_value),
        "right_value": float(right_value),
        "cfl_r": r,
        "diagnostics": {
            "method": "fdm_ftcs_explicit",
            "backend": "numpy",
            "cfl_r": r,
            "converged": True,
        },
    }
