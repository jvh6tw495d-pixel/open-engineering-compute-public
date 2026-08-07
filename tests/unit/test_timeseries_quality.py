"""Unit tests for timeseries quality kernel (S11)."""

from __future__ import annotations

import pytest

pytest.importorskip("pandas")

from oec.kernel.timeseries.quality import (  # noqa: E402
    clip_series,
    detect_outliers,
    normalize_series,
    rolling_window,
)

_TS = [
    "2024-01-01T00:00:00",
    "2024-01-01T01:00:00",
    "2024-01-01T02:00:00",
    "2024-01-01T03:00:00",
    "2024-01-01T04:00:00",
]


def test_detect_outliers_iqr() -> None:
    # Tukey fences: spike is clear under IQR even with small n
    out = detect_outliers(_TS, [1.0, 2.0, 100.0, 2.5, 1.5], method="iqr", threshold=1.5)
    assert out["n_outliers"] >= 1
    assert 2 in out["outlier_indices"]


def test_detect_outliers_zscore_extreme() -> None:
    # Need a stronger spike for sample z-score with n=5 (masking effect)
    out = detect_outliers(_TS, [1.0, 1.1, 1.0, 1.05, 1000.0], method="zscore", threshold=1.5)
    assert out["n_outliers"] >= 1
    assert 4 in out["outlier_indices"]


def test_clip_series() -> None:
    out = clip_series(_TS, [1.0, 2.0, 100.0, 2.5, 1.5], lower=0.0, upper=10.0)
    assert max(out["values"]) <= 10.0
    assert out["n_changed"] >= 1


def test_normalize_minmax() -> None:
    out = normalize_series(_TS, [0.0, 5.0, 10.0, 15.0, 20.0], method="minmax")
    assert out["values"][0] == pytest.approx(0.0)
    assert out["values"][-1] == pytest.approx(1.0)


def test_rolling_mean() -> None:
    out = rolling_window(_TS, [1.0, 2.0, 3.0, 4.0, 5.0], window=3, how="mean")
    assert len(out["values"]) == 5
    assert out["values"][2] == pytest.approx(2.0)
