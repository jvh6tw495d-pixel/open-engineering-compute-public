"""Regular time grid generator (S10 leftover). Merit: pandas."""

from __future__ import annotations

from typing import Any

import pandas as pd


def build_timegrid(
    start: str,
    end: str,
    *,
    freq: str,
    timezone: str | None = None,
    closed: str | None = None,
) -> dict[str, Any]:
    """Build inclusive regular datetime index from start to end at ``freq``."""
    if not freq:
        raise ValueError("freq is required")
    # pandas date_range
    kwargs: dict[str, Any] = {"start": start, "end": end, "freq": freq}
    if timezone:
        kwargs["tz"] = timezone
    if closed is not None:
        # pandas 2.x uses inclusive=
        kwargs["inclusive"] = closed
    idx = pd.date_range(**kwargs)
    stamps = [ts.isoformat() for ts in idx]
    return {
        "timestamps": stamps,
        "n_points": len(stamps),
        "freq": freq,
        "start": stamps[0] if stamps else None,
        "end": stamps[-1] if stamps else None,
        "timezone": timezone,
        "backend": "pandas",
    }
