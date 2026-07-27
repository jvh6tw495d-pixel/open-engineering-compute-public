"""Simple forecasting helpers (closed form, no SciPy/pandas algorithm).

Naive, seasonal-naive, and mean forecasters over a lead window. Mirrors
Hyndman & Athanasopoulos §3 — no iterative solver is used.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def forecast_simple(
    series: list[float],
    *,
    steps_ahead: int,
    method: str,
    period: int | None = None,
) -> dict[str, Any]:
    """Forecast ``steps_ahead`` steps past the end of ``series``."""
    if steps_ahead < 1:
        raise ValueError("steps_ahead must be >= 1")
    arr: Any = np.array(series, dtype=float)
    if arr.ndim != 1 or arr.size < 1:
        raise ValueError("series must be a non-empty 1-D list")

    if method == "naive":
        last = float(arr[-1])
        point = [last] * steps_ahead
    elif method == "mean":
        m = float(arr.mean())
        point = [m] * steps_ahead
    elif method == "seasonal_naive":
        if period is None or period < 1:
            raise ValueError("seasonal_naive requires period >= 1")
        if arr.size < period:
            raise ValueError("series must contain at least one full period")
        # Point for lead step t (1-indexed) is series[-period + (t-1) mod period]
        tail = arr[-period:]
        point = [float(tail[(t - 1) % period]) for t in range(1, steps_ahead + 1)]
    else:
        raise ValueError(f"unsupported method {method!r}")

    return {
        "method": method,
        "steps_ahead": steps_ahead,
        "n_series": int(arr.size),
        "period": period,
        "forecast": point,
        "backend": "numpy",
        "converged": None,
    }
