"""Nonparametric bootstrap helpers (NumPy). Merit: NumPy.

Closed-form point estimate plus percentile bootstrap confidence interval
for a single numeric statistic of a 1-D sample. OEC only resamples; no
statistical distribution code is reimplemented (ADR 0008).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np


def _statistic(sample: np.ndarray, kind: str) -> float:
    if kind == "mean":
        return float(np.mean(sample))
    if kind == "median":
        return float(np.median(sample))
    if kind == "variance":
        return float(np.var(sample, ddof=1)) if sample.size > 1 else 0.0
    raise ValueError(f"unsupported statistic kind {kind!r}")


@dataclass(frozen=True)
class BootstrapResult:
    statistic: str
    point_estimate: float
    n: int
    n_resamples: int
    confidence_level: float
    lower: float
    upper: float
    backend: str


def bootstrap_ci(
    samples: list[float],
    *,
    statistic: str = "mean",
    confidence_level: float = 0.95,
    n_resamples: int = 2000,
    seed: int | None = None,
) -> BootstrapResult:
    """Bootstrap percentile CI for ``statistic`` of ``samples``."""
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must lie in (0, 1)")
    if n_resamples < 1:
        raise ValueError("n_resamples must be >= 1")
    arr: Any = np.array(samples, dtype=float)
    if arr.ndim != 1:
        raise ValueError("samples must be 1-D")
    n = int(arr.size)
    if n < 1:
        raise ValueError("samples must be non-empty")

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(n_resamples, n))
    resampled = arr[indices]
    if statistic == "mean":
        statistic_values = resampled.mean(axis=1)
    elif statistic == "median":
        statistic_values = np.median(resampled, axis=1)
    elif statistic == "variance":
        statistic_values = resampled.var(axis=1, ddof=1) if n > 1 else np.zeros(n_resamples)
    else:
        raise ValueError(f"unsupported statistic {statistic!r}")

    alpha = 1.0 - confidence_level
    lower = float(np.quantile(statistic_values, alpha / 2.0))
    upper = float(np.quantile(statistic_values, 1.0 - alpha / 2.0))
    point = _statistic(arr, statistic)
    return BootstrapResult(
        statistic=statistic,
        point_estimate=point,
        n=n,
        n_resamples=n_resamples,
        confidence_level=confidence_level,
        lower=lower,
        upper=upper,
        backend="numpy",
    )


StatisticFn = Callable[[np.ndarray], float]
