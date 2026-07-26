"""Unit tests for S7′ feasibility/scenarios and S23–S26 opt advanced."""

from __future__ import annotations

import pytest

from oec.kernel.optimization.feasibility import check_feasibility, scenario_batch
from oec.kernel.optimization.multiobjective import weighted_sum_lp
from oec.kernel.optimization.qp import solve_qp
from oec.kernel.timeseries.timegrid import build_timegrid

pytest.importorskip("highspy")

_DIET = {
    "ops_version": "0.1.0",
    "problem_class": "lp",
    "sense": "min",
    "variables": [
        {"name": "x", "kind": "continuous", "lower": 0, "upper": 1},
        {"name": "y", "kind": "continuous", "lower": 0, "upper": 1},
    ],
    "constraints": [{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
    "objective": {"coeffs": {"x": 1, "y": 1}},
}


def test_check_feasibility_diet() -> None:
    out = check_feasibility(_DIET)
    assert out["feasible"] is True
    assert out["solver_status"] == "optimal"


def test_check_feasibility_infeasible_constraints() -> None:
    ops = {
        **_DIET,
        "constraints": [
            {"name": "low", "coeffs": {"x": 1, "y": 1}, "sense": "<=", "rhs": 0.5},
            {"name": "high", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 2.0},
        ],
    }
    out = check_feasibility(ops)
    assert out["feasible"] is False


def test_scenario_batch_rhs() -> None:
    out = scenario_batch(_DIET, path="constraint:cover.rhs", values=[0.5, 1.0, 2.5])
    assert out["n_scenarios"] == 3
    assert out["n_optimal"] >= 2


def test_scenario_batch_objective_coeff() -> None:
    out = scenario_batch(_DIET, path="objective.coeffs.x", values=[1.0, 5.0])
    assert out["n_scenarios"] == 2
    assert all(r["solver_status"] == "optimal" for r in out["scenarios"])


def test_scenario_batch_variable_upper() -> None:
    out = scenario_batch(_DIET, path="variable:x.upper", values=[0.0, 1.0])
    assert out["n_scenarios"] == 2


def test_scenario_batch_rejects_empty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        scenario_batch(_DIET, path="constraint:cover.rhs", values=[])


def test_scenario_batch_bad_path() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        scenario_batch(_DIET, path="foo.bar", values=[1.0])


def test_solve_qp_identity() -> None:
    out = solve_qp(
        [[2.0, 0.0], [0.0, 2.0]],
        [-2.0, -4.0],
        bounds=[[0.0, None], [0.0, None]],
        x0=[0.0, 0.0],
    )
    assert out["success"] is True
    assert out["x"][0] == pytest.approx(1.0, abs=1e-3)
    assert out["x"][1] == pytest.approx(2.0, abs=1e-3)


def test_solve_qp_with_eq_and_ub() -> None:
    # min x^2 + y^2 s.t. x+y=1, x>=0,y>=0
    out = solve_qp(
        [[2.0, 0.0], [0.0, 2.0]],
        [0.0, 0.0],
        bounds=[[0.0, None], [0.0, None]],
        a_eq=[[1.0, 1.0]],
        b_eq=[1.0],
        a_ub=[[1.0, 0.0]],
        b_ub=[1.0],
        x0=[0.5, 0.5],
    )
    assert out["success"] is True
    assert abs(out["x"][0] + out["x"][1] - 1.0) < 1e-4


def test_solve_qp_rejects_nonsquare() -> None:
    with pytest.raises(ValueError, match="square"):
        solve_qp([[1.0, 0.0]], [1.0, 2.0])


def test_weighted_sum_lp() -> None:
    out = weighted_sum_lp(
        _DIET,
        objectives=[{"x": 1, "y": 1}, {"x": 2, "y": 0}],
        weights=[0.5, 0.5],
    )
    assert out["success"] is True
    assert out["solver_status"] == "optimal"
    assert len(out["objective_values"]) == 2


def test_weighted_sum_rejects_negative_weight() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        weighted_sum_lp(_DIET, objectives=[{"x": 1}], weights=[-1.0])


def test_timegrid_hourly() -> None:
    out = build_timegrid("2024-01-01T00:00:00", "2024-01-01T03:00:00", freq="1h")
    assert out["n_points"] == 4
    assert out["timestamps"][0].startswith("2024-01-01")
