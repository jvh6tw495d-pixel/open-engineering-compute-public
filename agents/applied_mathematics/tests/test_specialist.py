"""S20: Applied Mathematics Specialist acceptance tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.applied_mathematics.specialist import (  # noqa: E402
    AppliedMathematicsSpecialist,
)

from oec.execution.models import ExecutionStatus  # noqa: E402


@pytest.fixture
def specialist() -> AppliedMathematicsSpecialist:
    return AppliedMathematicsSpecialist(skills_root=_ROOT / "skills")


def test_demo_sqrt2(specialist: AppliedMathematicsSpecialist) -> None:
    report = specialist.run_demo("sqrt2")
    assert report.skill_id == "mathematics.solve_root"
    assert report.execution is not None
    assert report.execution.status in {
        ExecutionStatus.VERIFIED,
        ExecutionStatus.VALIDATED,
        ExecutionStatus.CONVERGED_WITH_WARNINGS,
        ExecutionStatus.APPROXIMATE,
    }
    root = report.execution.result.get("root")
    assert root is not None
    assert abs(float(root) - 1.41421356237) < 1e-6
    assert report.execution.run_id in report.narrative


def test_demo_matrix_properties(specialist: AppliedMathematicsSpecialist) -> None:
    report = specialist.run_demo("matrix_properties")
    assert report.skill_id == "linear.matrix_properties"
    assert report.execution is not None
    assert report.execution.result["rank"] == 2
    assert report.execution.run_id in report.narrative


def test_demo_monte_carlo(specialist: AppliedMathematicsSpecialist) -> None:
    report = specialist.run_demo("monte_carlo")
    assert report.skill_id == "statistics.monte_carlo"
    assert report.execution is not None
    # E[x^2] on U(0,1) = 1/3
    mean = float(report.execution.result["mean"])
    assert abs(mean - 1.0 / 3.0) < 0.05


def test_unknown_demo_raises(specialist: AppliedMathematicsSpecialist) -> None:
    with pytest.raises(ValueError, match="Unknown demo"):
        specialist.run_demo("not_a_real_demo")
