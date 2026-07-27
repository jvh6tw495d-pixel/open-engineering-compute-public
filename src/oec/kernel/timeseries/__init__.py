"""Time-series helpers (pandas/NumPy). Merit: pandas/NumPy; OEC governs contracts."""

from oec.kernel.timeseries.backtest import backtest
from oec.kernel.timeseries.forecast import forecast_simple
from oec.kernel.timeseries.lag import lag_features
from oec.kernel.timeseries.ops import (
    align_series,
    fill_missing,
    power_to_energy,
    resample_series,
)
from oec.kernel.timeseries.quality import (
    clip_series,
    detect_outliers,
    normalize_series,
    rolling_window,
)
from oec.kernel.timeseries.timegrid import build_timegrid

__all__ = [
    "align_series",
    "backtest",
    "build_timegrid",
    "clip_series",
    "detect_outliers",
    "fill_missing",
    "forecast_simple",
    "lag_features",
    "normalize_series",
    "power_to_energy",
    "resample_series",
    "rolling_window",
]
