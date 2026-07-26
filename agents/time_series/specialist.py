"""Time-Series Specialist v0.1 — quality/ops skills via OEC only."""

from __future__ import annotations

from agents.common import SkillSpecialist

_TS = [
    "2024-01-01T00:00:00",
    "2024-01-01T01:00:00",
    "2024-01-01T02:00:00",
    "2024-01-01T03:00:00",
    "2024-01-01T04:00:00",
]


class TimeSeriesSpecialist(SkillSpecialist):
    """Maps TS demos → timeseries.* skills (pandas merit under OEC contract)."""

    name = "time_series_specialist"
    demos = {
        "resample": (
            "timeseries.resample",
            {
                "timestamps": [
                    "2024-01-01T00:00:00",
                    "2024-01-01T00:30:00",
                    "2024-01-01T01:00:00",
                    "2024-01-01T01:30:00",
                ],
                "values": [1.0, 3.0, 2.0, 4.0],
                "freq": "1h",
                "how": "mean",
            },
        ),
        "fill_missing": (
            "timeseries.fill_missing",
            {
                "timestamps": [
                    "2024-01-01T00:00:00",
                    "2024-01-01T01:00:00",
                    "2024-01-01T02:00:00",
                ],
                "values": [1.0, None, 3.0],
                "method": "ffill",
            },
        ),
        "detect_outliers": (
            "timeseries.detect_outliers",
            {
                "timestamps": _TS,
                "values": [1.0, 2.0, 100.0, 2.5, 1.5],
                "method": "iqr",
                "threshold": 1.5,
            },
        ),
        "clip": (
            "timeseries.clip",
            {
                "timestamps": _TS,
                "values": [1.0, 2.0, 100.0, 2.5, 1.5],
                "lower": 0.0,
                "upper": 10.0,
            },
        ),
        "normalize": (
            "timeseries.normalize",
            {
                "timestamps": _TS,
                "values": [0.0, 5.0, 10.0, 15.0, 20.0],
                "method": "minmax",
            },
        ),
        "rolling": (
            "timeseries.rolling",
            {
                "timestamps": _TS,
                "values": [1.0, 2.0, 3.0, 4.0, 5.0],
                "window": 3,
                "how": "mean",
            },
        ),
        "power_to_energy": (
            "timeseries.power_to_energy",
            {
                "timestamps": [
                    "2024-01-01T00:00:00",
                    "2024-01-01T01:00:00",
                ],
                "power": [1.0, 1.0],
                "power_unit": "kW",
                "energy_unit": "kWh",
            },
        ),
    }
