"""LTI state-space simulation. Merit: NumPy / SciPy."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.linalg import expm


def simulate_state_space(
    a: list[list[float]],
    b: list[list[float]],
    c: list[list[float]],
    d: list[list[float]],
    u: list[list[float]],
    x0: list[float],
    *,
    dt: float,
    time_base: str = "discrete",
) -> dict[str, Any]:
    """Simulate ``x⁺ = Ax + Bu``, ``y = Cx + Du`` (discrete) or c2d + same.

    Parameters
    ----------
    u:
        Input sequence shape ``(n_steps, n_inputs)``.
    x0:
        Initial state length ``n``.
    dt:
        Sample period (required for continuous discretisation; used as
        step label for discrete).
    time_base:
        ``"discrete"`` treats A,B as discrete; ``"continuous"`` uses
        zero-order-hold discretisation via matrix exponential.
    """
    if dt <= 0:
        raise ValueError("dt must be > 0")
    if time_base not in {"discrete", "continuous"}:
        raise ValueError("time_base must be 'discrete' or 'continuous'")

    a_m = np.asarray(a, dtype=float)
    b_m = np.asarray(b, dtype=float)
    c_m = np.asarray(c, dtype=float)
    d_m = np.asarray(d, dtype=float)
    u_m = np.asarray(u, dtype=float)
    x = np.asarray(x0, dtype=float).reshape(-1)

    if a_m.ndim != 2 or a_m.shape[0] != a_m.shape[1]:
        raise ValueError("A must be square")
    n = a_m.shape[0]
    if x.shape[0] != n:
        raise ValueError("x0 length must match A")
    if b_m.ndim != 2 or b_m.shape[0] != n:
        raise ValueError("B rows must match A")
    n_u = b_m.shape[1]
    if c_m.ndim != 2 or c_m.shape[1] != n:
        raise ValueError("C columns must match A")
    n_y = c_m.shape[0]
    if d_m.shape != (n_y, n_u):
        raise ValueError("D shape must be (n_outputs, n_inputs)")
    if u_m.ndim == 1:
        u_m = u_m.reshape(-1, 1)
    if u_m.ndim != 2 or u_m.shape[1] != n_u:
        raise ValueError("u must have shape (n_steps, n_inputs)")

    if time_base == "continuous":
        # ZOH discretisation: Ad = exp(A dt), Bd = A^{-1}(Ad-I)B when A invertible;
        # otherwise integrate via block matrix exponential.
        m = n + n_u
        block = np.zeros((m, m), dtype=float)
        block[:n, :n] = a_m
        block[:n, n:] = b_m
        e = expm(block * float(dt))
        a_d = e[:n, :n]
        b_d = e[:n, n:]
    else:
        a_d, b_d = a_m, b_m

    n_steps = int(u_m.shape[0])
    xs: list[list[float]] = []
    ys: list[list[float]] = []
    ts: list[float] = []
    x_k = x.copy()
    for k in range(n_steps):
        uk = u_m[k]
        yk = c_m @ x_k + d_m @ uk
        xs.append([float(v) for v in x_k.tolist()])
        ys.append([float(v) for v in np.asarray(yk, dtype=float).reshape(-1).tolist()])
        ts.append(float(k * dt))
        x_k = a_d @ x_k + b_d @ uk

    return {
        "t": ts,
        "x": xs,
        "y": ys,
        "n_steps": n_steps,
        "n_states": n,
        "n_inputs": n_u,
        "n_outputs": n_y,
        "dt": float(dt),
        "time_base": time_base,
        "backend": "numpy" if time_base == "discrete" else "scipy",
        "converged": None,
    }
