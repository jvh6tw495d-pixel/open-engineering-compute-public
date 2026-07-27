"""Linear uncertainty propagation (delta method). Merit: NumPy."""

from __future__ import annotations

from typing import Any

import numpy as np


def propagate_linear(
    jacobian: list[list[float]] | list[float],
    covariance: list[list[float]],
    *,
    nominal: list[float] | None = None,
) -> dict[str, Any]:
    """First-order (linear) uncertainty propagation.

    For a mapping ``y ≈ J x`` (or scalar ``y`` with gradient row), the
    output covariance is ``J Σ Jᵀ``.

    Parameters
    ----------
    jacobian:
        Shape ``(m, n)`` or length-``n`` gradient for a scalar output.
    covariance:
        Symmetric ``(n, n)`` input covariance.
    nominal:
        Optional nominal input vector (length ``n``) recorded for provenance.
    """
    jac = np.asarray(jacobian, dtype=float)
    if jac.ndim == 1:
        jac = jac.reshape(1, -1)
    if jac.ndim != 2:
        raise ValueError("jacobian must be 1-D or 2-D")
    cov = np.asarray(covariance, dtype=float)
    if cov.ndim != 2 or cov.shape[0] != cov.shape[1]:
        raise ValueError("covariance must be square 2-D")
    n = cov.shape[0]
    if jac.shape[1] != n:
        raise ValueError("jacobian columns must match covariance size")
    if not np.allclose(cov, cov.T, atol=1e-10):
        raise ValueError("covariance must be symmetric")
    # Soft positive-semidefinite check via eigenvalues.
    eig = np.linalg.eigvalsh(cov)
    if float(np.min(eig)) < -1e-8:
        raise ValueError("covariance must be positive semi-definite")

    out_cov = jac @ cov @ jac.T
    if out_cov.shape == (1, 1):
        variance = float(out_cov[0, 0])
        std = float(np.sqrt(max(variance, 0.0)))
        return {
            "output_dim": 1,
            "variance": variance,
            "std": std,
            "covariance": [[variance]],
            "nominal": None if nominal is None else [float(v) for v in nominal],
            "backend": "numpy",
            "converged": None,
            "method": "linear_delta",
        }

    variances = [float(out_cov[i, i]) for i in range(out_cov.shape[0])]
    stds = [float(np.sqrt(max(v, 0.0))) for v in variances]
    return {
        "output_dim": int(out_cov.shape[0]),
        "variance": variances,
        "std": stds,
        "covariance": [[float(v) for v in row] for row in out_cov.tolist()],
        "nominal": None if nominal is None else [float(v) for v in nominal],
        "backend": "numpy",
        "converged": None,
        "method": "linear_delta",
    }
