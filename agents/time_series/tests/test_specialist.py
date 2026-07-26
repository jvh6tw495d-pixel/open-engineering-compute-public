"""S21: Time-Series Specialist acceptance tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

pytest.importorskip("pandas")

from agents.time_series.specialist import TimeSeriesSpecialist  # noqa: E402

from oec.execution.models import ExecutionStatus  # noqa: E402

_OK = {
    ExecutionStatus.VERIFIED,
    ExecutionStatus.VALIDATED,
    ExecutionStatus.CONVERGED_WITH_WARNINGS,
    ExecutionStatus.APPROXIMATE,
}


@pytest.fixture
def specialist() -> TimeSeriesSpecialist:
    return TimeSeriesSpecialist(skills_root=_ROOT / "skills")


def test_demo_detect_outliers(specialist: TimeSeriesSpecialist) -> None:
    report = specialist.run_demo("detect_outliers")
    assert report.skill_id == "timeseries.detect_outliers"
    assert report.execution is not None
    assert report.execution.status in _OK
    assert report.execution.result["n_outliers"] >= 1
    assert report.execution.run_id in report.narrative


def test_demo_rolling(specialist: TimeSeriesSpecialist) -> None:
    report = specialist.run_demo("rolling")
    assert report.skill_id == "timeseries.rolling"
    assert report.execution is not None
    assert report.execution.status in _OK
    assert len(report.execution.result["values"]) == 5


def test_demo_clip(specialist: TimeSeriesSpecialist) -> None:
    report = specialist.run_demo("clip")
    assert report.execution is not None
    assert max(report.execution.result["values"]) <= 10.0


def test_demo_resample(specialist: TimeSeriesSpecialist) -> None:
    report = specialist.run_demo("resample")
    assert report.skill_id == "timeseries.resample"
    assert report.execution is not None
    assert report.execution.status in _OK
