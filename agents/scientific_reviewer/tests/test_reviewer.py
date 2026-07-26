"""Phase G: Scientific Reviewer tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

pytest.importorskip("highspy")

from datetime import UTC, datetime  # noqa: E402

from agents.optimization_specialist.specialist import OptimizationSpecialist  # noqa: E402
from agents.scientific_reviewer.reviewer import ScientificReviewer  # noqa: E402

from oec.common import VersionedRef  # noqa: E402
from oec.execution.models import ExecutionResult, ExecutionStatus  # noqa: E402


def test_reviewer_passes_clean_solve() -> None:
    specialist = OptimizationSpecialist(skills_root=_ROOT / "skills")
    report = specialist.run_demo("diet")
    assert report.execution is not None
    review = ScientificReviewer().review(report.ops, report.execution)
    assert review.passed is True
    codes = {c.code: c.ok for c in review.checks}
    assert codes.get("ops_valid") is True
    assert codes.get("provenance_present") is True


def test_reviewer_flags_forged_optimal_claim() -> None:
    specialist = OptimizationSpecialist(skills_root=_ROOT / "skills")
    report = specialist.run_demo("diet")
    assert report.execution is not None
    # Forge: claim wrong objective
    review = ScientificReviewer().review(
        report.ops,
        report.execution,
        claimed_objective=999.0,
    )
    assert review.passed is False
    assert any(c.code == "claimed_numbers" and not c.ok for c in review.checks)


def test_reviewer_flags_inconsistent_status() -> None:
    forged = ExecutionResult(
        status=ExecutionStatus.VALIDATED,
        skill=VersionedRef(id="optimization.lp", version="0.1.0"),
        method=VersionedRef(id="highs_lp", version="0.1.0"),
        result={
            "solver_status": "infeasible",
            "objective_value": None,
            "primal": {},
            "dual": {},
            "feasibility_issues": [],
            "backend": "highs",
        },
        diagnostics={"converged": True},
        provenance={},
        started_at=datetime.now(UTC),
    )
    ops = OptimizationSpecialist(skills_root=_ROOT / "skills").demo_ops_from_label("diet")
    review = ScientificReviewer().review(ops, forged)
    assert review.passed is False
    assert any(
        c.code in {"status_solver_consistency", "no_false_optimal", "feasibility_on_infeasible"}
        and not c.ok
        for c in review.checks
    )


def test_reviewer_flags_invalid_ops() -> None:
    forged = ExecutionResult(
        status=ExecutionStatus.FAILED,
        skill=VersionedRef(id="optimization.lp", version="0.1.0"),
        method=VersionedRef(id="highs_lp", version="0.1.0"),
        started_at=datetime.now(UTC),
        provenance={"input_hash": "abc"},
        run_id="x",
    )
    review = ScientificReviewer().review({"not": "ops"}, forged)
    assert review.passed is False
    assert any(c.code == "ops_valid" and not c.ok for c in review.checks)
