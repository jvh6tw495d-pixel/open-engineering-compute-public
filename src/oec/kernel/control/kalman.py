"""Discrete linear Kalman filter. Merit: NumPy (standard KF equations)."""

from __future__ import annotations

from typing import Any

import numpy as np


def kalman_filter_linear(
    a: list[list[float]],
    b: list[list[float]] | None,
    c: list[list[float]],
    q: list[list[float]],
    r: list[list[float]],
    z: list[list[float]],
    x0: list[float],
    p0: list[list[float]],
    *,
    u: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Time-invariant discrete linear Kalman filter.

    Model: ``x = A x + B u + w``, ``z = C x + v`` with ``w~N(0,Q)``, ``v~N(0,R)``.
    """
    a_m = np.asarray(a, dtype=float)
    c_m = np.asarray(c, dtype=float)
    q_m = np.asarray(q, dtype=float)
    r_m = np.asarray(r, dtype=float)
    z_m = np.asarray(z, dtype=float)
    x = np.asarray(x0, dtype=float).reshape(-1)
    p = np.asarray(p0, dtype=float)

    if a_m.ndim != 2 or a_m.shape[0] != a_m.shape[1]:
        raise ValueError("A must be square")
    n = a_m.shape[0]
    if x.shape[0] != n or p.shape != (n, n):
        raise ValueError("x0/P0 dimensions must match A")
    if c_m.ndim != 2 or c_m.shape[1] != n:
        raise ValueError("C columns must match state dim")
    n_y = c_m.shape[0]
    if q_m.shape != (n, n):
        raise ValueError("Q must be n x n")
    if r_m.shape != (n_y, n_y):
        raise ValueError("R must be n_y x n_y")
    if z_m.ndim == 1:
        z_m = z_m.reshape(-1, 1)
    if z_m.ndim != 2 or z_m.shape[1] != n_y:
        raise ValueError("z must have shape (n_steps, n_outputs)")

    n_steps = int(z_m.shape[0])
    if b is None:
        b_m = np.zeros((n, 1), dtype=float)
        u_m = np.zeros((n_steps, 1), dtype=float)
    else:
        b_m = np.asarray(b, dtype=float)
        if b_m.ndim != 2 or b_m.shape[0] != n:
            raise ValueError("B rows must match state dim")
        if u is None:
            raise ValueError("u is required when B is provided")
        u_m = np.asarray(u, dtype=float)
        if u_m.ndim == 1:
            u_m = u_m.reshape(-1, 1)
        if u_m.shape[0] != n_steps or u_m.shape[1] != b_m.shape[1]:
            raise ValueError("u shape must be (n_steps, n_inputs)")

    xs: list[list[float]] = []
    innovs: list[list[float]] = []
    for k in range(n_steps):
        # Predict
        x_pred = a_m @ x + b_m @ u_m[k]
        p_pred = a_m @ p @ a_m.T + q_m
        # Update
        zk = z_m[k]
        innov = zk - c_m @ x_pred
        s = c_m @ p_pred @ c_m.T + r_m
        # K = P C^T S^{-1}
        k_gain = p_pred @ c_m.T @ np.linalg.inv(s)
        x = x_pred + k_gain @ innov
        p = (np.eye(n) - k_gain @ c_m) @ p_pred
        xs.append([float(v) for v in np.asarray(x, dtype=float).reshape(-1).tolist()])
        innovs.append([float(v) for v in np.asarray(innov, dtype=float).reshape(-1).tolist()])

    return {
        "x_filtered": xs,
        "innovations": innovs,
        "n_steps": n_steps,
        "n_states": n,
        "n_outputs": n_y,
        "backend": "numpy",
        "converged": None,
        "method": "discrete_linear_kalman",
    }
