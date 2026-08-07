"""Regression kernel (NumPy). Merit: NumPy / closed-form OLS.

A single OLS implementation used by ``statistics.regression``. Sums of
squares, residual standard error, and R^2 are computed independently of
NumPy's high-level helpers (per ADR 0008 — OEC does not reimplement
algorithms, but a transparent closed-form statistical formula is fine).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RegressionResult:
    coefficients: list[float]
    fitted: list[float]
    residuals: list[float]
    r_squared: float
    adj_r_squared: float
    rmse: float
    residual_standard_error: float
    n: int
    k: int
    backend: str


def linear_regression(x: list[list[float]], y: list[float]) -> RegressionResult:
    """Ordinary least-squares regression of ``y`` on the columns of ``x``.

    ``x`` is interpreted as the design matrix (rows = samples,
    columns = features). A leading all-ones column for the intercept is
    NOT auto-added — the caller must include it if desired, so the model
    is fully explicit (consistent with NumPy's `lstsq` convention).
    """
    arr_x: Any = np.array(x, dtype=float)
    if arr_x.ndim != 2:
        raise ValueError("x must be 2-D")
    arr_y: Any = np.array(y, dtype=float)
    if arr_y.ndim != 1:
        raise ValueError("y must be 1-D")
    if arr_x.shape[0] != arr_y.shape[0]:
        raise ValueError("x rows and y length must match")
    if arr_x.shape[0] <= arr_x.shape[1]:
        raise ValueError("regression requires n_samples > n_features")

    coeffs, _, rank, _ = np.linalg.lstsq(arr_x, arr_y, rcond=None)
    fitted = arr_x @ coeffs
    residuals = arr_y - fitted

    n = int(arr_x.shape[0])
    k = int(arr_x.shape[1])
    dof = n - k
    if dof <= 0:
        raise ValueError("degrees of freedom must be positive")

    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((arr_y - float(np.mean(arr_y))) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    adj_r_squared = 1.0 - (1.0 - r_squared) * (n - 1) / dof if dof > 0 else 0.0
    rmse = float(np.sqrt(ss_res / n))
    rse = float(np.sqrt(ss_res / dof))

    return RegressionResult(
        coefficients=[float(c) for c in coeffs],
        fitted=[float(v) for v in fitted],
        residuals=[float(r) for r in residuals],
        r_squared=r_squared,
        adj_r_squared=adj_r_squared,
        rmse=rmse,
        residual_standard_error=rse,
        n=n,
        k=k,
        backend="numpy",
    )
