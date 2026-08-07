"""Lag and window feature helpers for OEC timeseries skills.

Closed-form slicing of an input series — no SciPy/pandas numeric code is
reimplemented here (ADR 0008). Pairs lag columns with the destination
index they predict; lag = 0 reflects the present sample, lag = k is
k positions earlier.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def lag_features(
    values: list[float],
    lags: list[int],
) -> dict[str, Any]:
    """Lag columns for the requested list of non-negative lag indices.

    Returns a dict of parallel lists all of length ``n - max(lags)``;
    the first ``max(lags)`` samples are only usable as regressors and so
    they are dropped from the aligned output, guaranteeing that every row
    has a value for every lag column. ``y`` is the slice of the values
    array aligned to the kept rows (i.e. after the dropping front).
    """
    if not isinstance(lags, list) or not lags:
        raise ValueError("lags must be a non-empty list of non-negative ints")
    if any(not isinstance(lag, int) or lag < 0 for lag in lags):
        raise ValueError("lag indices must be non-negative integers")
    arr: Any = np.array(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError("values must be a 1-D list")
    max_lag = max(lags)
    n = int(arr.size)
    if n <= max_lag:
        raise ValueError("len(values) must exceed max(lags)")
    columns: dict[int, list[float]] = {}
    n_keep = n - max_lag
    for lag in lags:
        # y[j] aligns with values[j + max_lag]; the lag-L regressor at that
        # row is values[(j + max_lag) - L]. So the aligned column slice is
        # values[max_lag - L : max_lag - L + n_keep] (length n_keep).
        offset = max_lag - lag
        columns[lag] = [float(x) for x in arr[offset : offset + n_keep]]
    return {
        "lags": sorted(set(lags)),
        "columns": {str(lag): columns[lag] for lag in columns},
        "y": [float(x) for x in arr[max_lag:]],
        "n_keep": n_keep,
        "n_original": n,
        "max_lag": max_lag,
    }
