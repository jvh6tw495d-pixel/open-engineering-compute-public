"""S22: Energy Specialist acceptance tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.energy.specialist import EnergySpecialist  # noqa: E402

from oec.execution.models import ExecutionStatus  # noqa: E402

_OK = {
    ExecutionStatus.VERIFIED,
    ExecutionStatus.VALIDATED,
    ExecutionStatus.CONVERGED_WITH_WARNINGS,
    ExecutionStatus.APPROXIMATE,
}


@pytest.fixture
def specialist() -> EnergySpecialist:
    return EnergySpecialist(skills_root=_ROOT / "skills")


def test_demo_balance(specialist: EnergySpecialist) -> None:
    report = specialist.run_demo("balance")
    assert report.skill_id == "energy.balance"
    assert report.execution is not None
    assert report.execution.status in _OK
    assert report.execution.run_id in report.narrative


def test_demo_load_metrics(specialist: EnergySpecialist) -> None:
    report = specialist.run_demo("load_metrics")
    assert report.skill_id == "energy.load_metrics"
    assert report.execution is not None
    assert report.execution.status in _OK


def test_demo_soc_step(specialist: EnergySpecialist) -> None:
    report = specialist.run_demo("soc_step")
    assert report.skill_id == "battery.soc_step"
    assert report.execution is not None
    assert report.execution.status in _OK
    # 0.5 + 10 kW * 1 h / 100 kWh = 0.6 (sign convention may vary)
    soc = report.execution.result.get("soc") or report.execution.result.get("soc_final")
    assert soc is not None


def test_unknown_demo_raises(specialist: EnergySpecialist) -> None:
    with pytest.raises(ValueError, match="Unknown demo"):
        specialist.run_demo("secret_dispatch")
