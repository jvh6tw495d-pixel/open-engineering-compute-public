"""Unit tests for v2.3 Wave C optimization kernels."""

from __future__ import annotations

import pytest

from oec.kernel.optimization.cvar import cvar_lp
from oec.kernel.optimization.highs import HighsNotAvailableError
from oec.kernel.optimization.pareto import pareto_weighted_sum
from oec.kernel.optimization.robust import robust_lp_box_rhs

_OPS = {
    "ops_version": "0.1.0",
    "problem_class": "lp",
    "sense": "min",
    "variables": [
        {"name": "x", "kind": "continuous", "lower": 0, "upper": 10},
        {"name": "y", "kind": "continuous", "lower": 0, "upper": 10},
    ],
    "constraints": [{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
    "objective": {"coeffs": {"x": 1, "y": 1}},
}


def _skip_if_no_highs(result: dict[str, object]) -> None:
    issues = result.get("feasibility_issues") or []
    if result.get("solver_status") == "other" and any("not installed" in str(i) for i in issues):
        pytest.skip("highspy not installed")
    points = result.get("points")
    if isinstance(points, list) and points:
        p0 = points[0]
        if isinstance(p0, dict) and any(
            "not installed" in str(i) for i in (p0.get("feasibility_issues") or [])
        ):
            pytest.skip("highspy not installed")


def test_pareto_weighted_sum() -> None:
    try:
        out = pareto_weighted_sum(
            _OPS,
            objective_a={"x": 1, "y": 2},
            objective_b={"x": 2, "y": 1},
            n_points=5,
        )
    except HighsNotAvailableError:
        pytest.skip("highspy not installed")
    _skip_if_no_highs(out)
    assert out["n_points_requested"] == 5
    assert out["n_solved_optimal"] >= 1
    assert out["n_nondominated"] >= 1


def test_cvar_lp_basic() -> None:
    try:
        out = cvar_lp(
            decision_vars=[{"name": "x", "lower": 0.0, "upper": 5.0}],
            loss_scenarios=[{"x": 1.0}, {"x": 3.0}],
            alpha=0.5,
            structural_constraints=[{"name": "lb", "coeffs": {"x": 1}, "sense": ">=", "rhs": 1.0}],
        )
    except HighsNotAvailableError:
        pytest.skip("highspy not installed")
    _skip_if_no_highs(out)
    assert out["method"] == "rockafellar_uryasev"
    if out["converged"]:
        assert out["cvar"] is not None
        assert out["decision"]["x"] >= 1.0 - 1e-8


def test_robust_lp_box_rhs() -> None:
    try:
        out = robust_lp_box_rhs(_OPS, rhs_uncertainty={"cover": 0.2})
    except HighsNotAvailableError:
        pytest.skip("highspy not installed")
    _skip_if_no_highs(out)
    assert out["rhs_adjusted"]["cover"]["rhs_robust"] == pytest.approx(1.2)
    if out["converged"]:
        assert out["objective_value"] == pytest.approx(1.2)
