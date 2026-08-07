"""Phase G: Optimization Specialist acceptance tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Repo root on path so `agents.*` imports work without packaging.
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

pytest.importorskip("highspy")

from agents.optimization_specialist.specialist import OptimizationSpecialist  # noqa: E402


def test_demo_diet_pipeline() -> None:
    specialist = OptimizationSpecialist(skills_root=_ROOT / "skills")
    report = specialist.run_demo("diet")
    assert report.ops_valid is True
    assert report.problem_class == "lp"
    assert report.skill_id == "optimization.lp"
    assert report.execution is not None
    assert report.execution.result["solver_status"] == "optimal"
    assert abs(report.execution.result["objective_value"] - 1.0) < 1e-8
    assert report.execution.run_id in report.narrative
    assert "objective_value" in report.narrative
    assert "HiGHS" in report.narrative or "highs" in report.narrative.lower()


def test_demo_knapsack_milp() -> None:
    specialist = OptimizationSpecialist(skills_root=_ROOT / "skills")
    report = specialist.run_demo("knapsack")
    assert report.problem_class == "milp"
    assert report.execution is not None
    assert report.execution.result["solver_status"] == "optimal"
    assert abs(report.execution.result["objective_value"] - 3.0) < 1e-8


def test_invalid_ops_does_not_execute() -> None:
    specialist = OptimizationSpecialist(skills_root=_ROOT / "skills")
    report = specialist.execute_ops({"problem_class": "lp"})  # incomplete
    assert report.execution is None
    assert report.ops_valid is False or report.missing_fields or report.validation_error
