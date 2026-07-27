"""Confidence interval helpers for sample statistics (Montgomery & Runger).

Closed-form Student-t / Gaussian intervals for the mean. Merit: NumPy/SciPy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class IntervalResult:
    mean: float
    sample_standard_deviation: float | None
    population_standard_deviation: float | None
    dispersion_used: str
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
    population_standard_deviation: float | None = None,
    # Deprecated alias rejected at call sites that still pass known_variance
    known_variance: bool | None = None,
) -> IntervalResult:
    """Two-sided CI for the population mean.

    * Student-t when ``population_standard_deviation`` is omitted (needs n>=2).
    * Normal/Z when a finite positive population standard deviation is given.
    """
    if known_variance is not None:
        raise ValueError(
            "known_variance is removed; pass population_standard_deviation "
            "(positive finite float) for a Z-interval, or omit it for Student-t"
        )
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must lie in (0, 1)")
    arr: Any = np.array(samples, dtype=float)
    if arr.ndim != 1:
        raise ValueError("samples must be 1-D")
    n = int(arr.size)
    if n < 1:
        raise ValueError("samples must be non-empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError("samples must be finite")

    mean = float(np.mean(arr))
    sample_sd: float | None = float(np.std(arr, ddof=1)) if n >= 2 else None
    alpha = 1.0 - confidence_level

    if population_standard_deviation is not None:
        sigma = float(population_standard_deviation)
        if not math.isfinite(sigma) or sigma <= 0.0:
            raise ValueError(
                "population_standard_deviation must be finite and strictly positive"
            )
        z = float(stats.norm.ppf(1.0 - alpha / 2.0))
        half = z * sigma / float(np.sqrt(n))
        return IntervalResult(
            mean=mean,
            sample_standard_deviation=sample_sd,
            population_standard_deviation=sigma,
            dispersion_used="population_standard_deviation",
            n=n,
            confidence_level=confidence_level,
            distribution="gaussian",
            df=None,
            lower=mean - half,
            upper=mean + half,
            half_width=half,
            backend="scipy.stats",
        )

    if n < 2:
        raise ValueError("Student-t CI requires n >= 2 (or population_standard_deviation)")
    assert sample_sd is not None
    if sample_sd == 0.0:
        # Degenerate sample: interval collapses to the mean
        half = 0.0
    else:
        df = float(n - 1)
        t = float(stats.t.ppf(1.0 - alpha / 2.0, df))
        half = t * sample_sd / float(np.sqrt(n))
    df_out = float(n - 1)
    return IntervalResult(
        mean=mean,
        sample_standard_deviation=sample_sd,
        population_standard_deviation=None,
        dispersion_used="sample_standard_deviation",
        n=n,
        confidence_level=confidence_level,
        distribution="student_t",
        df=df_out,
        lower=mean - half,
        upper=mean + half,
        half_width=half,
        backend="scipy.stats",
    )
