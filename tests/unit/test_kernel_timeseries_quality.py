"""Direct kernel tests for oec.kernel.timeseries.quality (v2.5.1 coverage push).

Targets the branches flagged as untested in
docs/implementation/v2.5-critical-path-coverage.md ("outlier/gap-detection
edge branches", quality.py at 67%): each skill only exercises one example
per method/how variant, leaving the alternate branches (iqr vs zscore,
degenerate zero-variance inputs, and rolling's sum/min/max/std paths)
untested at the kernel level.
"""

from __future__ import annotations

import pytest

from oec.kernel.timeseries.quality import (
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


class TestDetectOutliers:
    def test_zscore_flags_the_far_outlier(self) -> None:
        out = detect_outliers(_TS, [1.0, 2.0, 100.0, 2.5, 1.5], method="zscore", threshold=1.5)
        assert out["method"] == "zscore"
        assert 2 in out["outlier_indices"]
        assert out["n_outliers"] == len(out["outlier_indices"])

    def test_zscore_constant_series_flags_nothing(self) -> None:
        """std==0 branch: every value is identical, mask must be all-False
        (division by zero would otherwise be attempted)."""
        out = detect_outliers(_TS, [5.0] * 5, method="zscore", threshold=1.0)
        assert out["outlier_indices"] == []
        assert out["n_outliers"] == 0

    def test_iqr_flags_the_far_outlier(self) -> None:
        out = detect_outliers(_TS, [1.0, 2.0, 100.0, 2.5, 1.5], method="iqr", threshold=1.5)
        assert out["method"] == "iqr"
        assert 2 in out["outlier_indices"]

    def test_iqr_finds_no_outliers_in_a_tight_cluster(self) -> None:
        out = detect_outliers(_TS, [1.0, 1.1, 0.9, 1.05, 0.95], method="iqr", threshold=3.0)
        assert out["outlier_indices"] == []


class TestClipSeries:
    def test_lower_only(self) -> None:
        out = clip_series(_TS, [-5.0, 1.0, 2.0, 3.0, 4.0], lower=0.0)
        assert out["values"][0] == 0.0
        assert out["n_changed"] == 1
        assert out["upper"] is None

    def test_upper_only(self) -> None:
        out = clip_series(_TS, [1.0, 2.0, 3.0, 4.0, 50.0], upper=10.0)
        assert out["values"][-1] == 10.0
        assert out["n_changed"] == 1

    def test_lower_and_upper(self) -> None:
        out = clip_series(_TS, [-5.0, 2.0, 3.0, 4.0, 50.0], lower=0.0, upper=10.0)
        assert out["values"][0] == 0.0
        assert out["values"][-1] == 10.0
        assert out["n_changed"] == 2

    def test_no_change_when_already_within_bounds(self) -> None:
        out = clip_series(_TS, [1.0, 2.0, 3.0, 4.0, 5.0], lower=0.0, upper=10.0)
        assert out["n_changed"] == 0


class TestNormalizeSeries:
    def test_minmax(self) -> None:
        out = normalize_series(_TS, [0.0, 5.0, 10.0, 15.0, 20.0], method="minmax")
        assert out["values"][0] == 0.0
        assert out["values"][-1] == 1.0
        assert out["params"] == {"min": 0.0, "max": 20.0}

    def test_minmax_constant_series_is_all_zero(self) -> None:
        """hi==lo branch: a constant series has zero range."""
        out = normalize_series(_TS, [7.0] * 5, method="minmax")
        assert out["values"] == [0.0] * 5

    def test_zscore(self) -> None:
        out = normalize_series(_TS, [1.0, 2.0, 3.0, 4.0, 5.0], method="zscore")
        assert out["params"]["mean"] == pytest.approx(3.0)
        assert sum(out["values"]) == pytest.approx(0.0, abs=1e-9)

    def test_zscore_constant_series_is_all_zero(self) -> None:
        """std==0 branch."""
        out = normalize_series(_TS, [7.0] * 5, method="zscore")
        assert out["values"] == [0.0] * 5


class TestRollingWindow:
    @pytest.mark.parametrize("how", ["mean", "sum", "min", "max"])
    def test_each_reducer_runs(self, how: str) -> None:
        out = rolling_window(_TS, [1.0, 2.0, 3.0, 4.0, 5.0], window=3, how=how)
        assert out["how"] == how
        assert out["n_points"] == 5
        # window=3, min_periods=1: first point is always defined
        assert out["values"][0] is not None

    def test_std_reducer_runs(self) -> None:
        out = rolling_window(_TS, [1.0, 2.0, 3.0, 4.0, 5.0], window=3, how="std")
        assert out["how"] == "std"
        assert out["n_points"] == 5
        assert out["values"][-1] is not None

    def test_std_first_point_is_none(self) -> None:
        """A single-point window has no std; pandas reports NaN -> None."""
        out = rolling_window(_TS, [1.0, 2.0, 3.0, 4.0, 5.0], window=3, how="std")
        assert out["values"][0] is None

    def test_window_below_one_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="window"):
            rolling_window(_TS, [1.0, 2.0, 3.0, 4.0, 5.0], window=0)
