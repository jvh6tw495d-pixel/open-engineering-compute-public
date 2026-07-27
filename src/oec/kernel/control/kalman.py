"""Discrete linear Kalman filter with covariance hygiene (B23-01). Merit: NumPy."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

_SYM_TOL = 1e-10
_EIG_TOL = 1e-10
_COND_WARN = 1e12


class KalmanNumericalError(ValueError):
    """Structured numerical failure in the Kalman filter (not a bare LinAlgError)."""

    def __init__(self, message: str, *, code: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _require_square_symmetric(m: np.ndarray, name: str) -> None:
    if m.ndim != 2 or m.shape[0] != m.shape[1]:
        raise ValueError(f"{name} must be square")
    if not np.allclose(m, m.T, atol=_SYM_TOL):
        raise ValueError(f"{name} must be symmetric within tol={_SYM_TOL}")


def _require_psd(m: np.ndarray, name: str, *, strict: bool = False) -> None:
    _require_square_symmetric(m, name)
    eig = np.linalg.eigvalsh(0.5 * (m + m.T))
    floor = _EIG_TOL if not strict else 0.0
    if float(np.min(eig)) < -floor:
        raise ValueError(f"{name} must be positive semi-definite (min eig={float(np.min(eig))})")
    if strict and float(np.min(eig)) <= _EIG_TOL:
        raise ValueError(f"{name} must be positive definite (min eig={float(np.min(eig))})")


def _symmetrize(m: np.ndarray) -> np.ndarray:
    out: np.ndarray = 0.5 * (m + m.T)
    return out


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
    """Time-invariant discrete linear Kalman filter with Joseph covariance update.

    Model: ``x⁺ = A x + B u + w``, ``z = C x + v`` with ``w~N(0,Q)``, ``v~N(0,R)``.

    Validates symmetry and definiteness of Q (PSD), R (PD), P0 (PSD).
    Uses ``solve`` for the innovation system; raises
    :class:`KalmanNumericalError` on singular/ill-conditioned innovation.
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

    _require_psd(q_m, "Q", strict=False)
    _require_psd(p, "P0", strict=False)
    _require_psd(r_m, "R", strict=True)

    q_m = _symmetrize(q_m)
    r_m = _symmetrize(r_m)
    p = _symmetrize(p)

    if z_m.ndim == 1:
        z_m = z_m.reshape(-1, 1)
    if z_m.ndim != 2 or z_m.shape[1] != n_y:
        raise ValueError("z must have shape (n_steps, n_outputs)")
    if not np.all(np.isfinite(z_m)):
        raise ValueError("z must be finite")

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
    gains: list[list[list[float]]] = []
    p_filtered: list[list[list[float]]] = []
    max_cond = 0.0

    eye = np.eye(n)
    for k in range(n_steps):
        x_pred = a_m @ x + b_m @ u_m[k]
        p_pred = _symmetrize(a_m @ p @ a_m.T + q_m)

        zk = z_m[k]
        innov = zk - c_m @ x_pred
        s = _symmetrize(c_m @ p_pred @ c_m.T + r_m)

        try:
            cond = float(np.linalg.cond(s))
        except np.linalg.LinAlgError as exc:
            raise KalmanNumericalError(
                "failed to assess innovation covariance conditioning",
                code="innovation_cond_failed",
                details={"step": k},
            ) from exc
        max_cond = max(max_cond, cond)
        if not math.isfinite(cond) or cond > 1e16:
            raise KalmanNumericalError(
                "innovation covariance is singular or extremely ill-conditioned",
                code="innovation_singular",
                details={"step": k, "cond": cond},
            )

        # K = P C^T S^{-1} via solve (S K^T = C P)
        try:
            k_gain = np.linalg.solve(s, c_m @ p_pred.T).T
        except np.linalg.LinAlgError as exc:
            raise KalmanNumericalError(
                "innovation solve failed (singular S)",
                code="innovation_singular",
                details={"step": k},
            ) from exc

        x = x_pred + k_gain @ innov
        # Joseph form: (I-KC) P (I-KC)^T + K R K^T
        i_kc = eye - k_gain @ c_m
        p = _symmetrize(i_kc @ p_pred @ i_kc.T + k_gain @ r_m @ k_gain.T)

        # Soft PSD clamp for numerical noise
        eigvals, eigvecs = np.linalg.eigh(p)
        eigvals = np.maximum(eigvals, 0.0)
        p = _symmetrize(eigvecs @ np.diag(eigvals) @ eigvecs.T)

        xs.append([float(v) for v in np.asarray(x).reshape(-1).tolist()])
        innovs.append([float(v) for v in np.asarray(innov).reshape(-1).tolist()])
        gains.append([[float(v) for v in row] for row in k_gain.tolist()])
        p_filtered.append([[float(v) for v in row] for row in p.tolist()])

    return {
        "x_filtered": xs,
        "innovations": innovs,
        "kalman_gains": gains,
        "p_filtered": p_filtered,
        "n_steps": n_steps,
        "n_states": n,
        "n_outputs": n_y,
        "max_innovation_condition": max_cond,
        "symmetry_tolerance": _SYM_TOL,
        "backend": "numpy",
        "converged": None,
        "method": "discrete_linear_kalman_joseph",
    }
