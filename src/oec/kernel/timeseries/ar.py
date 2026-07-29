"""Autoregressive / autocorrelation kernel (NumPy only — ADR 0008).

Sample autocorrelation, sample partial autocorrelation (PACF), and
Yule-Walker AR coefficient estimation, all built on one shared
Levinson-Durbin Toeplitz-solve engine. No SciPy/pandas primitive exists
for the Levinson-Durbin recursion itself (statsmodels has one, but OEC
does not depend on statsmodels); it is hand-rolled here from the
textbook recursion (see ``references.md`` of the skills that call this
module) rather than duplicated per skill.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def autocorrelation(
    series: list[float],
    *,
    nlags: int,
    method: str = "biased",
    demean: bool = True,
) -> dict[str, Any]:
    """Sample autocorrelation function of ``series`` at lags ``0..nlags``.

    ``method="biased"`` divides every lagged cross-sum by ``n`` (the
    classic estimator, and the one that guarantees the resulting sequence
    is a valid positive-semidefinite autocorrelation sequence — required
    for :func:`levinson_durbin` to always succeed on it).
    ``method="unbiased"`` (a.k.a. "adjusted") divides the lag-``k``
    cross-sum by ``n - k`` instead; it is not guaranteed positive
    semidefinite for small samples.
    """
    x: Any = np.asarray(series, dtype=float)
    if x.ndim != 1 or x.size < 2:
        raise ValueError("series must be a 1-D sequence of length >= 2")
    if not np.isfinite(x).all():
        raise ValueError("series must contain only finite values")
    if method not in {"biased", "unbiased"}:
        raise ValueError(f"unsupported method {method!r}")
    n = int(x.size)
    if nlags < 1:
        raise ValueError("nlags must be >= 1")
    if nlags >= n:
        raise ValueError("nlags must be < len(series)")

    y: Any = x - x.mean() if demean else x
    c0 = float(np.dot(y, y))
    if c0 == 0.0:
        raise ValueError("series has zero variance; autocorrelation is undefined")

    acf: list[float] = [1.0]
    for k in range(1, nlags + 1):
        raw = float(np.dot(y[: n - k], y[k:]))
        if method == "biased":
            acf.append(raw / c0)
        else:
            acf.append(raw * n / ((n - k) * c0))

    return {
        "acf": acf,
        "n": n,
        "nlags": nlags,
        "method": method,
        "demean": demean,
        "backend": "numpy",
        "converged": None,
    }


def levinson_durbin(acf: list[float]) -> dict[str, Any]:
    """Solve the Yule-Walker Toeplitz system by the Levinson-Durbin recursion.

    ``acf`` is an autocovariance/autocorrelation sequence ``[r0, r1, ...,
    rp]`` with ``r0`` (the process variance) strictly positive. Returns AR
    coefficients at every intermediate order ``1..p``, the reflection
    coefficients (identically the partial autocorrelation at each lag),
    and the prediction-error variance sequence ``E_0..E_p``.

    A real, valid (positive-semidefinite) autocorrelation sequence always
    yields ``|reflection coefficient| < 1`` at every step. If that
    invariant breaks — which can happen for an arbitrary or
    "unbiased"-estimated sequence handed in directly, as opposed to one
    produced by :func:`autocorrelation` with ``method="biased"`` — the
    recursion is honestly stopped rather than continued into a
    numerically meaningless region; ``is_positive_definite`` is ``False``
    and ``order_reached`` reports how far it got.
    """
    r: Any = np.asarray(acf, dtype=float)
    if r.ndim != 1 or r.size < 2:
        raise ValueError("autocorrelation must be a 1-D sequence of length >= 2")
    if not np.isfinite(r).all():
        raise ValueError("autocorrelation must contain only finite values")
    if r[0] <= 0:
        raise ValueError("autocorrelation[0] (the process variance) must be positive")

    p = int(r.size) - 1
    a: Any = np.zeros(p + 1)
    err_prev = float(r[0])
    error_by_order: list[float] = [err_prev]
    reflection_coefficients: list[float] = []
    ar_coefficients_by_order: list[list[float]] = []
    is_positive_definite = True
    order_reached = 0

    for k in range(1, p + 1):
        if err_prev <= 0.0:
            is_positive_definite = False
            break
        acc = float(r[k] - np.dot(a[1:k], r[k - 1 : 0 : -1]))
        phi_kk = acc / err_prev
        if abs(phi_kk) >= 1.0:
            is_positive_definite = False
            break
        a_prev = a.copy()
        a[k] = phi_kk
        for j in range(1, k):
            a[j] = a_prev[j] - phi_kk * a_prev[k - j]
        err_prev = err_prev * (1.0 - phi_kk**2)

        reflection_coefficients.append(float(phi_kk))
        error_by_order.append(float(err_prev))
        ar_coefficients_by_order.append([float(x) for x in a[1 : k + 1]])
        order_reached = k

    final_ar = ar_coefficients_by_order[-1] if ar_coefficients_by_order else []

    return {
        "ar_coefficients": final_ar,
        "reflection_coefficients": reflection_coefficients,
        "prediction_error_variance": error_by_order,
        "ar_coefficients_by_order": ar_coefficients_by_order,
        "order_requested": p,
        "order_reached": order_reached,
        "is_positive_definite": is_positive_definite,
        "backend": "numpy",
        "converged": None,
    }


def ar_yule_walker(
    series: list[float],
    *,
    order: int,
    demean: bool = True,
) -> dict[str, Any]:
    """Yule-Walker AR(``order``) coefficient estimate for ``series``.

    Estimates the sample autocorrelation up to ``order`` (biased
    estimator — the one :func:`levinson_durbin` is guaranteed to solve
    without hitting a non-positive-definite stop), then solves the
    resulting Toeplitz system via :func:`levinson_durbin`. The reported
    ``innovation_variance`` rescales the recursion's normalized
    prediction-error variance by the series' actual sample variance.
    """
    if order < 1:
        raise ValueError("order must be >= 1")
    acf_out = autocorrelation(series, nlags=order, method="biased", demean=demean)
    ld = levinson_durbin(acf_out["acf"])

    x: Any = np.asarray(series, dtype=float)
    y: Any = x - x.mean() if demean else x
    sample_variance = float(np.dot(y, y)) / x.size

    return {
        "ar_coefficients": ld["ar_coefficients"],
        "order_requested": order,
        "order_reached": ld["order_reached"],
        "is_positive_definite": ld["is_positive_definite"],
        "innovation_variance": sample_variance * ld["prediction_error_variance"][-1],
        "sample_variance": sample_variance,
        "acf_used": acf_out["acf"],
        "n": acf_out["n"],
        "demean": demean,
        "method": "yule_walker_levinson_durbin",
        "backend": "numpy",
        "converged": None,
    }


def pacf(
    series: list[float],
    *,
    nlags: int,
    method: str = "levinson-durbin",
    demean: bool = True,
) -> dict[str, Any]:
    """Sample partial autocorrelation function of ``series`` via Levinson-Durbin.

    ``pacf[0]`` is defined as ``1.0`` by convention; ``pacf[k]`` for
    ``k >= 1`` is the Levinson-Durbin reflection coefficient at lag
    ``k``. The underlying sample autocorrelation always uses the biased
    estimator, so the recursion is mathematically guaranteed to reach
    ``nlags`` without hitting the non-positive-definite stop condition.
    """
    if method != "levinson-durbin":
        raise ValueError(f"unsupported pacf method {method!r}")
    acf_out = autocorrelation(series, nlags=nlags, method="biased", demean=demean)
    ld = levinson_durbin(acf_out["acf"])

    return {
        "pacf": [1.0, *ld["reflection_coefficients"]],
        "n": acf_out["n"],
        "nlags": nlags,
        "method": method,
        "order_reached": ld["order_reached"],
        "is_positive_definite": ld["is_positive_definite"],
        "backend": "numpy",
        "converged": None,
    }
