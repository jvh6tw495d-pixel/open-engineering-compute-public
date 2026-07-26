"""Time-series helpers (pandas). Merit: pandas/NumPy; OEC governs contracts."""

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

__all__ = [
    "align_series",
    "clip_series",
    "detect_outliers",
    "fill_missing",
    "normalize_series",
    "power_to_energy",
    "resample_series",
    "rolling_window",
]
