"""Generic time-series operations via pandas (Phase D)."""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd  # type: ignore[import-untyped]


def _apply_timezone(idx: pd.DatetimeIndex, timezone: str | None) -> pd.DatetimeIndex:
    if not timezone:
        return idx
    return idx.tz_localize(timezone) if idx.tz is None else idx.tz_convert(timezone)


def _to_series(timestamps: list[str], values: list[float], timezone: str | None) -> pd.Series:
    idx = _apply_timezone(pd.to_datetime(timestamps, utc=False), timezone)
    series = pd.Series(values, index=idx, dtype=float)
    series = series.sort_index()
    if series.index.has_duplicates:
        raise ValueError("timestamps must be unique")
    return series


def resample_series(
    timestamps: list[str],
    values: list[float],
    *,
    freq: str,
    how: Literal["mean", "sum", "min", "max", "last"] = "mean",
    timezone: str | None = None,
) -> dict[str, Any]:
    series = _to_series(timestamps, values, timezone)
    resampler = series.resample(freq)
    if how == "mean":
        out = resampler.mean()
    elif how == "sum":
        out = resampler.sum()
    elif how == "min":
        out = resampler.min()
    elif how == "max":
        out = resampler.max()
    else:
        out = resampler.last()
    out = out.dropna(how="all")
    return {
        "timestamps": [ts.isoformat() for ts in out.index],
        "values": [float(v) for v in out.tolist()],
        "freq": freq,
        "how": how,
        "n_points": int(len(out)),
    }


def align_series(
    timestamps_a: list[str],
    values_a: list[float],
    timestamps_b: list[str],
    values_b: list[float],
    *,
    how: Literal["inner", "outer"] = "inner",
    timezone: str | None = None,
) -> dict[str, Any]:
    a = _to_series(timestamps_a, values_a, timezone)
    b = _to_series(timestamps_b, values_b, timezone)
    frame = pd.concat([a.rename("a"), b.rename("b")], axis=1, join=how)
    if how == "inner":
        frame = frame.dropna()
    return {
        "timestamps": [ts.isoformat() for ts in frame.index],
        "values_a": [None if pd.isna(v) else float(v) for v in frame["a"].tolist()],
        "values_b": [None if pd.isna(v) else float(v) for v in frame["b"].tolist()],
        "how": how,
        "n_points": int(len(frame)),
    }


def fill_missing(
    timestamps: list[str],
    values: list[float | None],
    *,
    method: Literal["ffill", "bfill", "linear"] = "ffill",
    timezone: str | None = None,
) -> dict[str, Any]:
    idx = _apply_timezone(pd.to_datetime(timestamps, utc=False), timezone)
    series = pd.Series(values, index=idx, dtype=float).sort_index()
    before = int(series.isna().sum())
    if method == "ffill":
        filled = series.ffill()
    elif method == "bfill":
        filled = series.bfill()
    else:
        filled = series.interpolate(method="linear")
    after = int(filled.isna().sum())
    return {
        "timestamps": [ts.isoformat() for ts in filled.index],
        "values": [None if pd.isna(v) else float(v) for v in filled.tolist()],
        "method": method,
        "n_filled": before - after,
        "n_remaining_missing": after,
    }


def power_to_energy(
    timestamps: list[str],
    power_values: list[float],
    *,
    power_unit: str = "kW",
    energy_unit: str = "kWh",
    timezone: str | None = None,
) -> dict[str, Any]:
    """Trapezoidal integration of power over time → energy per interval and total.

    Assumes power is average-ready instantaneous series; Δt from timestamps in hours.
    Only kW→kWh and W→Wh scale factors are built-in (dimensionally consistent pairs).
    """
    series = _to_series(timestamps, power_values, timezone)
    if len(series) < 2:
        raise ValueError("power_to_energy requires at least 2 timestamps")

    scale = _power_energy_scale(power_unit, energy_unit)
    # Energy between points i and i+1: average power * Δt_hours * scale
    times = series.index
    powers = series.to_numpy(dtype=float)
    interval_energy: list[float] = []
    for i in range(len(powers) - 1):
        dt_hours = (times[i + 1] - times[i]).total_seconds() / 3600.0
        if dt_hours <= 0:
            raise ValueError("timestamps must be strictly increasing")
        e = 0.5 * (powers[i] + powers[i + 1]) * dt_hours * scale
        interval_energy.append(float(e))
    total = float(sum(interval_energy))
    return {
        "interval_energy": interval_energy,
        "total_energy": total,
        "energy_unit": energy_unit,
        "power_unit": power_unit,
        "n_intervals": len(interval_energy),
        "method": "trapezoidal",
    }


def _power_energy_scale(power_unit: str, energy_unit: str) -> float:
    pu = power_unit.strip().lower()
    eu = energy_unit.strip().lower()
    pairs = {
        ("kw", "kwh"): 1.0,
        ("w", "wh"): 1.0,
        ("w", "kwh"): 1.0 / 1000.0,
        ("kw", "wh"): 1000.0,
        ("mw", "mwh"): 1.0,
        ("mw", "kwh"): 1000.0,
    }
    key = (pu, eu)
    if key not in pairs:
        raise ValueError(
            f"unsupported power/energy unit pair {power_unit!r}/{energy_unit!r}; "
            "supported: kW/kWh, W/Wh, W/kWh, kW/Wh, MW/MWh, MW/kWh"
        )
    return pairs[key]
