"""Direct kernel tests for oec.kernel.optimization.feasibility (v2.5.1 coverage push).

Targets the branches flagged as untested in
docs/implementation/v2.5-critical-path-coverage.md ("multi-issue aggregation
branches", feasibility.py at 77%). Existing dedicated tests for
optimization.infeasibility_explain already cover the feasible /
single_constraint_relaxation / no_single_relaxation tiers (see
skills/optimization/infeasibility_explain/tests/test_golden.py), so this
file focuses on what those don't: the budget_exhausted tier, and
scenario_batch's per-scenario-infeasible and _apply_path branches.

NOTE on the "multi-issue aggregation" branches themselves (the
`check_bound_conflicts` calls and the `not c.coeffs` empty-constraint checks
inside check_feasibility/explain_infeasibility/scenario_batch): every one of
these three functions calls `oec.ops.models.validate_ops(ops_document)`
first, and that Pydantic layer already rejects `lower > upper` variable
bounds *and* the OPS JSON Schema already requires `coeffs` to be a non-empty
object (`minProperties: 1`). That means the precheck branches these
functions were written to surface are unreachable through any of the three
public entrypoints as currently wired -- the low coverage here reflects
genuinely dead code, not merely undertested code. Flagged as a follow-up
(not fixed here: removing it is a design call, not a coverage-push change).
"""

from __future__ import annotations

import pytest

from oec.kernel.optimization.feasibility import (
    check_feasibility,
    explain_infeasibility,
    scenario_batch,
)

pytest.importorskip("highspy")


def _base_ops(**overrides: object) -> dict:
    ops: dict = {
        "ops_version": "0.1.0",
        "problem_class": "lp",
        "sense": "min",
        "variables": [{"name": "x", "kind": "continuous", "lower": 0, "upper": 1}],
        "constraints": [{"name": "use", "coeffs": {"x": 1}, "sense": ">=", "rhs": 0}],
        "objective": {"coeffs": {"x": 1}},
    }
    ops.update(overrides)
    return ops


class TestCheckFeasibility:
    def test_feasible_model(self) -> None:
        out = check_feasibility(_base_ops())
        assert out["feasible"] is True
        assert out["solver_status"] == "optimal"
        assert out["backend"] == "highs"

    def test_infeasible_via_solver(self) -> None:
        ops = _base_ops(
            constraints=[
                {"name": "c1", "coeffs": {"x": 1}, "sense": ">=", "rhs": 1},
                {"name": "c2", "coeffs": {"x": 1}, "sense": "<=", "rhs": 0},
            ]
        )
        out = check_feasibility(ops)
        assert out["feasible"] is False
        assert out["solver_status"] == "infeasible"
        assert out["backend"] == "highs"
        assert "HiGHS reported the problem as infeasible" in out["feasibility_issues"]


class TestScenarioBatch:
    def test_normal_sweep_reports_optimal_for_every_value(self) -> None:
        out = scenario_batch(_base_ops(), path="constraint:use.rhs", values=[0.0, 0.2, 0.4])
        assert out["n_scenarios"] == 3
        assert out["n_optimal"] == 3
        assert all(s["solver_status"] == "optimal" for s in out["scenarios"])

    def test_objective_coeffs_path_is_applied(self) -> None:
        out = scenario_batch(_base_ops(), path="objective.coeffs.x", values=[1.0, 2.0])
        assert out["n_scenarios"] == 2
        assert out["n_optimal"] == 2

    def test_variable_bound_path_is_applied(self) -> None:
        out = scenario_batch(_base_ops(), path="variable:x.upper", values=[0.5, 0.8])
        assert out["n_scenarios"] == 2

    def test_scenario_that_is_infeasible_via_solver_is_reported_not_raised(self) -> None:
        """A scenario whose swept RHS makes the LP infeasible (but keeps
        variable bounds valid, so it passes validate_ops) must surface as a
        per-scenario infeasible result, not raise or abort the whole sweep."""
        ops = _base_ops(constraints=[{"name": "cap", "coeffs": {"x": 1}, "sense": "<=", "rhs": 0}])
        out = scenario_batch(ops, path="constraint:cap.rhs", values=[1.0, -1.0])
        assert out["scenarios"][0]["solver_status"] == "optimal"
        assert out["scenarios"][1]["solver_status"] == "infeasible"
        assert out["scenarios"][1]["feasibility_issues"] == ["infeasible"]
        assert out["n_optimal"] == 1

    def test_empty_values_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            scenario_batch(_base_ops(), path="objective.coeffs.x", values=[])

    def test_too_many_scenarios_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="50"):
            scenario_batch(_base_ops(), path="objective.coeffs.x", values=list(range(51)))

    def test_unknown_constraint_path_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            scenario_batch(_base_ops(), path="constraint:nope.rhs", values=[1.0])

    def test_unknown_variable_path_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            scenario_batch(_base_ops(), path="variable:nope.upper", values=[1.0])

    def test_unsupported_path_shape_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="unsupported scenario path"):
            scenario_batch(_base_ops(), path="not.a.real.path", values=[1.0])


class TestExplainInfeasibility:
    def test_budget_exhausted_tier_when_drop_one_budget_is_zero(self) -> None:
        """An infeasible model with a nonzero solve budget too small to test
        every constraint must report budget_exhausted, not a false
        no_single_relaxation conclusion."""
        ops = _base_ops(
            constraints=[
                {"name": "c1", "coeffs": {"x": 1}, "sense": ">=", "rhs": 1},
                {"name": "c2", "coeffs": {"x": 1}, "sense": "<=", "rhs": 0},
            ]
        )
        out = explain_infeasibility(ops, max_drop_one_solves=0)
        assert out["tier"] == "budget_exhausted"
        assert out["feasible"] is False
        assert out["drop_one_solves_used"] == 0
        assert out["single_constraint_relaxations"] == []
