"""Confidence interval helpers for sample statistics (Montgomery & Runger).

Closed-form Student-t / Gaussian intervals for the mean; one-pass sample
mean and (sample) standard deviation from NumPy — no algorithm is
reimplemented here (ADR 0008).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class IntervalResult:
    mean: float
    sample_standard_deviation: float
    n: int
    confidence_level: float
    distribution: str
    df: float | None
    lower: float
    upper: float
    half_width: float
    backend: str


def confidence_interval_of_mean(
    samples: list[float],
    confidence_level: float = 0.95,
    *,
    known_variance: bool = False,
) -> IntervalResult:
    """Confidence interval for the population mean of ``samples``.

    Uses a Student-t interval (``df = n - 1``) by default; switches to the
    Gaussian interval when ``known_variance`` is true (σ known, large n).
    """
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must lie in (0, 1)")
    arr: Any = np.array(samples, dtype=float)
    if arr.ndim != 1:
        raise ValueError("samples must be 1-D")
    n = int(arr.size)
    if n < 1:
        raise ValueError("samples must be non-empty")
    if n == 1 and not known_variance:
        raise ValueError("Student-t CI requires n >= 2")

    mean = float(np.mean(arr))
    s = float(np.std(arr, ddof=1)) if n >= 2 else 0.0
    alpha = 1.0 - confidence_level

    if known_variance:
        z = float(stats.norm.ppf(1.0 - alpha / 2.0))
        half = z * s / float(np.sqrt(n))
        distribution = "gaussian"
        df: float | None = None
    else:
        df = float(n - 1)
        t = float(stats.t.ppf(1.0 - alpha / 2.0, df))
        half = t * s / float(np.sqrt(n))
        distribution = "student_t"

    return IntervalResult(
        mean=mean,
        sample_standard_deviation=s,
        n=n,
        confidence_level=confidence_level,
        distribution=distribution,
        df=df,
        lower=mean - half,
        upper=mean + half,
        half_width=half,
        backend="scipy.stats",
    )
