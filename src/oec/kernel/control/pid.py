"""Discrete PID controller. Merit: closed-form recurrence (no SciPy)."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

AntiWindup = Literal["none", "clamp"]


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
    anti_windup: AntiWindup = "none",
) -> dict[str, Any]:
    """Position-form discrete PID over aligned reference/measurement series.

    ``u[k] = Kp e[k] + Ki * I[k] + Kd (e[k]-e[k-1])/dt`` with optional
    saturation on ``u``.

    Anti-windup (B23-05)
    --------------------
    * ``none`` (default): integrator keeps accumulating under saturation
      (documented windup behaviour of the original Wave B skill).
    * ``clamp``: do not integrate further while the unsaturated command is
      outside ``[u_min, u_max]`` (when those bounds exist).
    """
    if dt <= 0:
        raise ValueError("dt must be > 0")
    if anti_windup not in {"none", "clamp"}:
        raise ValueError("anti_windup must be 'none' or 'clamp'")
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
    integral_term = np.zeros(n, dtype=float)
    integral = 0.0
    e_prev = 0.0
    saturated_steps = 0
    for k in range(n):
        # Candidate integration step
        integral_candidate = integral + float(e[k]) * dt
        derivative = (float(e[k]) - e_prev) / dt if k > 0 else 0.0
        # Provisional command with candidate integral
        uk_unsat = float(kp) * float(e[k]) + float(ki) * integral_candidate + float(kd) * derivative
        saturated = False
        uk = uk_unsat
        if u_min is not None and uk < u_min:
            uk = float(u_min)
            saturated = True
        if u_max is not None and uk > u_max:
            uk = float(u_max)
            saturated = True
        if saturated:
            saturated_steps += 1
            if anti_windup == "none":
                integral = integral_candidate
            # clamp: leave integral unchanged under saturation
        else:
            integral = integral_candidate
        integral_term[k] = float(ki) * integral
        u[k] = uk
        e_prev = float(e[k])

    return {
        "u": [float(v) for v in u.tolist()],
        "error": [float(v) for v in e.tolist()],
        "integral_term": [float(v) for v in integral_term.tolist()],
        "n": n,
        "kp": float(kp),
        "ki": float(ki),
        "kd": float(kd),
        "dt": float(dt),
        "saturated_steps": int(saturated_steps),
        "anti_windup": anti_windup,
        "backend": "numpy",
        "converged": None,
        "method": "position_pid_discrete",
    }
