"""Direct kernel tests for oec.kernel.timeseries.timegrid (v2.5.1 coverage push).

Targets the branches flagged as untested in
docs/implementation/v2.5-critical-path-coverage.md ("irregular-grid edge
cases", timegrid.py at 70%): the skill layer only ever passes start/end/freq/
timezone (no `closed`), so the timezone and `closed`/`inclusive` branches are
untested, along with the required-`freq` and empty-result edge cases.
"""

from __future__ import annotations

import pytest

from oec.kernel.timeseries.timegrid import build_timegrid


def test_basic_hourly_grid() -> None:
    out = build_timegrid("2024-01-01T00:00:00", "2024-01-01T02:00:00", freq="1h")
    assert out["n_points"] == 3
    assert out["start"] is not None
    assert out["end"] is not None
    assert out["backend"] == "pandas"
    assert out["timezone"] is None


def test_freq_is_required() -> None:
    with pytest.raises(ValueError, match="freq"):
        build_timegrid("2024-01-01T00:00:00", "2024-01-01T02:00:00", freq="")


def test_timezone_is_applied() -> None:
    out = build_timegrid("2024-01-01T00:00:00", "2024-01-01T02:00:00", freq="1h", timezone="UTC")
    assert out["timezone"] == "UTC"
    assert "+00:00" in out["start"] or "Z" in out["start"]


@pytest.mark.parametrize(
    ("closed", "expected_n"),
    [
        ("both", 3),
        ("left", 2),
        ("right", 2),
        ("neither", 1),
    ],
)
def test_closed_controls_endpoint_inclusion(closed: str, expected_n: int) -> None:
    out = build_timegrid("2024-01-01T00:00:00", "2024-01-01T02:00:00", freq="1h", closed=closed)
    assert out["n_points"] == expected_n


def test_neither_closed_on_a_single_step_range_is_empty() -> None:
    """start==end with closed='neither' excludes the only point -> empty grid."""
    out = build_timegrid("2024-01-01T00:00:00", "2024-01-01T00:00:00", freq="1h", closed="neither")
    assert out["n_points"] == 0
    assert out["timestamps"] == []
    assert out["start"] is None
    assert out["end"] is None
