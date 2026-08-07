"""Generic public finance metrics — no proprietary scoring or commercial VaR models.

Formulas are textbook / Basel-style historical VaR only.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def simple_returns(prices: list[float]) -> dict[str, Any]:
    """Simple returns r_t = p_t / p_{t-1} - 1 for consecutive prices."""
    if len(prices) < 2:
        raise ValueError("prices must have at least 2 points")
    arr: Any = np.asarray(prices, dtype=float)
    if np.any(arr[:-1] == 0.0):
        raise ValueError("prices used as denominators must be non-zero")
    rets: Any = (arr[1:] / arr[:-1]) - 1.0
    return {
        "returns": [float(x) for x in rets.tolist()],
        "n_returns": int(len(rets)),
        "method": "simple",
        "backend": "numpy",
    }


def max_drawdown(prices: list[float]) -> dict[str, Any]:
    """Maximum drawdown of a price series: min over t of (p_t / peak_t - 1)."""
    if len(prices) < 2:
        raise ValueError("prices must have at least 2 points")
    arr: Any = np.asarray(prices, dtype=float)
    if np.any(arr <= 0.0):
        raise ValueError("prices must be positive for max drawdown")
    peaks: Any = np.maximum.accumulate(arr)
    dd: Any = arr / peaks - 1.0
    idx = int(np.argmin(dd))
    return {
        "max_drawdown": float(dd[idx]),
        "max_drawdown_index": idx,
        "peak_price": float(peaks[idx]),
        "trough_price": float(arr[idx]),
        "drawdown_series": [float(x) for x in dd.tolist()],
        "backend": "numpy",
    }


def historical_var(
    returns: list[float],
    *,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Historical VaR (loss quantile) at ``confidence`` (e.g. 0.95 → 5% left tail).

    Returns a positive number meaning loss magnitude when the left tail is negative.
    Convention: VaR = -quantile(returns, 1-confidence) for loss-as-positive reporting
    when the quantile is negative; otherwise reports -quantile.
    """
    if not returns:
        raise ValueError("returns must be non-empty")
    if not 0.5 < confidence < 1.0:
        raise ValueError("confidence must be in (0.5, 1.0)")
    arr: Any = np.asarray(returns, dtype=float)
    alpha = 1.0 - float(confidence)
    q = float(np.quantile(arr, alpha))
    var_loss = float(-q)
    return {
        "var": var_loss,
        "quantile": q,
        "confidence": float(confidence),
        "alpha": alpha,
        "n": int(len(arr)),
        "method": "historical",
        "convention": "positive_var_is_loss",
        "backend": "numpy",
    }
