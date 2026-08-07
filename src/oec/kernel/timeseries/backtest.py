"""Rolling backtest harness for the simple forecasters.

Walks the end of a series with a sliding training window and evaluates the
naive / mean / seasonal_naive forecaster at each step. Reports per-step
MAE and RMSE, and the aggregate skill score against the naive baseline.

Closed form — no SciPy/pandas solver is invoked (ADR 0008): the
forecasters themselves are pure NumPy rollups in
``oec.kernel.timeseries.forecast``.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.timeseries.forecast import forecast_simple


def backtest(
    series: list[float],
    *,
    steps_ahead: int,
    method: str,
    period: int | None = None,
    n_evaluations: int | None = None,
) -> dict[str, Any]:
    """Rolling one-step backtest of ``method`` over the tail of ``series``.

    Each evaluation produces a single-step forecast and is compared
    against the held-out actual. Errors are aggregated as MAE and RMSE.
    """
    if steps_ahead < 1:
        raise ValueError("steps_ahead must be >= 1")
    arr: Any = np.array(series, dtype=float)
    if arr.ndim != 1 or arr.size < 1:
        raise ValueError("series must be a non-empty 1-D list")

    n = int(arr.size)
    if n_evaluations is None:
        n_evaluations = n - 1
    if n_evaluations < 1:
        raise ValueError("n_evaluations must be >= 1")
    start = n - n_evaluations
    if start < 1:
        raise ValueError("series is too short for n_evaluations")

    errors: list[float] = []
    for i in range(start, n):
        train = arr[:i].tolist()
        out = forecast_simple(
            train,
            steps_ahead=steps_ahead,
            method=method,
            period=period,
        )
        # Use only the first forecast step; the rest are not evaluable one-step ahead
        # without further held-out data.
        pred = float(out["forecast"][0])
        actual = float(arr[i])
        errors.append(actual - pred)

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.array(errors) ** 2)))

    # Skill score against the naive baseline (forecast = last value).
    naive_forecast = arr[:-1]
    naive_actual = arr[1:]
    naive_errors = naive_actual - naive_forecast
    # Align the skill-score baseline window to the backtest window.
    naive_errors = naive_errors[start - 1 :]
    naive_mae = float(np.mean(np.abs(naive_errors))) if naive_errors.size else 0.0
    skill_score = 1.0 - mae / naive_mae if naive_mae > 0 else 0.0

    return {
        "method": method,
        "steps_ahead": steps_ahead,
        "period": period,
        "n_series": n,
        "n_evaluations": int(n_evaluations),
        "mae": mae,
        "rmse": rmse,
        "naive_baseline_mae": naive_mae,
        "skill_score_vs_naive": skill_score,
        "errors": [float(e) for e in errors],
        "backend": "numpy",
        "converged": None,
    }
