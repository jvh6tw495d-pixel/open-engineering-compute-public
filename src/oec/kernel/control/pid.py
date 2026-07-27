"""Discrete PID controller. Merit: closed-form recurrence (no SciPy)."""

from __future__ import annotations

from typing import Any

import numpy as np


def pid_discrete(
    reference: list[float],
    measurement: list[float],
    *,
    kp: float,
    ki: float,
    kd: float,
    dt: float,
    u_min: float | None = None,
    u_max: float | None = None,
) -> dict[str, Any]:
    """Position-form discrete PID over aligned reference/measurement series.

    ``u[k] = Kp e[k] + Ki dt Σ e + Kd (e[k]-e[k-1])/dt`` with optional
    saturation on ``u``.
    """
    if dt <= 0:
        raise ValueError("dt must be > 0")
    if len(reference) != len(measurement):
        raise ValueError("reference and measurement must have equal length")
    if len(reference) < 1:
        raise ValueError("series must be non-empty")
    if u_min is not None and u_max is not None and u_min > u_max:
        raise ValueError("u_min must be <= u_max")

    r = np.asarray(reference, dtype=float)
    y = np.asarray(measurement, dtype=float)
    e = r - y
    n = int(e.size)
    u = np.zeros(n, dtype=float)
    integral = 0.0
    e_prev = 0.0
    saturated_steps = 0
    for k in range(n):
        integral += float(e[k]) * dt
        derivative = (float(e[k]) - e_prev) / dt if k > 0 else 0.0
        uk = float(kp) * float(e[k]) + float(ki) * integral + float(kd) * derivative
        if u_min is not None and uk < u_min:
            uk = float(u_min)
            saturated_steps += 1
        if u_max is not None and uk > u_max:
            uk = float(u_max)
            saturated_steps += 1
        u[k] = uk
        e_prev = float(e[k])

    return {
        "u": [float(v) for v in u.tolist()],
        "error": [float(v) for v in e.tolist()],
        "n": n,
        "kp": float(kp),
        "ki": float(ki),
        "kd": float(kd),
        "dt": float(dt),
        "saturated_steps": int(saturated_steps),
        "backend": "numpy",
        "converged": None,
        "method": "position_pid_discrete",
    }
