"""Time-series quality ops (Phase S11). Backend merit: pandas/NumPy."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd

from oec.kernel.timeseries.ops import _to_series


def detect_outliers(
    timestamps: list[str],
    values: list[float],
    *,
    method: Literal["zscore", "iqr"] = "zscore",
    threshold: float = 3.0,
    timezone: str | None = None,
) -> dict[str, Any]:
    series = _to_series(timestamps, values, timezone)
    arr = series.to_numpy(dtype=float)
    if method == "zscore":
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
        if std == 0.0:
            mask = np.zeros(len(arr), dtype=bool)
        else:
            mask = np.abs((arr - mean) / std) > float(threshold)
    else:
        q1, q3 = np.quantile(arr, [0.25, 0.75])
        iqr = float(q3 - q1)
        lo, hi = q1 - float(threshold) * iqr, q3 + float(threshold) * iqr
        mask = (arr < lo) | (arr > hi)
    idx = [int(i) for i, flag in enumerate(mask.tolist()) if flag]
    return {
        "method": method,
        "threshold": float(threshold),
        "outlier_indices": idx,
        "outlier_timestamps": [series.index[i].isoformat() for i in idx],
        "outlier_values": [float(arr[i]) for i in idx],
        "n_outliers": len(idx),
        "n_points": int(len(arr)),
    }


def clip_series(
    timestamps: list[str],
    values: list[float],
    *,
    lower: float | None = None,
    upper: float | None = None,
    timezone: str | None = None,
) -> dict[str, Any]:
    series = _to_series(timestamps, values, timezone)
    before = series.to_numpy(dtype=float).copy()
    clipped = series.clip(lower=lower, upper=upper)
    after = clipped.to_numpy(dtype=float)
    n_changed = int(np.sum(before != after))
    return {
        "timestamps": [ts.isoformat() for ts in clipped.index],
        "values": [float(v) for v in after.tolist()],
        "lower": lower,
        "upper": upper,
        "n_changed": n_changed,
    }


def normalize_series(
    timestamps: list[str],
    values: list[float],
    *,
    method: Literal["minmax", "zscore"] = "minmax",
    timezone: str | None = None,
) -> dict[str, Any]:
    series = _to_series(timestamps, values, timezone)
    arr = series.to_numpy(dtype=float)
    if method == "minmax":
        lo, hi = float(np.min(arr)), float(np.max(arr))
        norm = np.zeros_like(arr) if hi == lo else (arr - lo) / (hi - lo)
        meta = {"min": lo, "max": hi}
    else:
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
        norm = np.zeros_like(arr) if std == 0.0 else (arr - mean) / std
        meta = {"mean": mean, "std": std}
    return {
        "timestamps": [ts.isoformat() for ts in series.index],
        "values": [float(v) for v in norm.tolist()],
        "method": method,
        "params": meta,
    }


def rolling_window(
    timestamps: list[str],
    values: list[float],
    *,
    window: int,
    how: Literal["mean", "sum", "min", "max", "std"] = "mean",
    timezone: str | None = None,
) -> dict[str, Any]:
    if window < 1:
        raise ValueError("window must be >= 1")
    series = _to_series(timestamps, values, timezone)
    roll = series.rolling(window=window, min_periods=1)
    if how == "mean":
        out = roll.mean()
    elif how == "sum":
        out = roll.sum()
    elif how == "min":
        out = roll.min()
    elif how == "max":
        out = roll.max()
    else:
        out = roll.std()
    return {
        "timestamps": [ts.isoformat() for ts in out.index],
        "values": [None if pd.isna(v) else float(v) for v in out.tolist()],
        "window": int(window),
        "how": how,
        "n_points": int(len(out)),
    }
