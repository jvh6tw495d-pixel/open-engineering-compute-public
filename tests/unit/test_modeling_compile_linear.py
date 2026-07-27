"""Math IR linear compiler tests (ADR 0020)."""

from __future__ import annotations

import pytest

from oec.kernel.optimization.highs import HighsNotAvailableError
from oec.modeling.compile_linear import compile_linear, to_ops_problem
from oec.modeling.ir import MathProblem, Symbol

pytest.importorskip("highspy")


def test_to_ops_problem_requires_objective() -> None:
    problem = MathProblem(symbols=[Symbol(name="x")])
    with pytest.raises(ValueError, match="not a linear_program"):
        to_ops_problem(problem)


def test_to_ops_problem_translates_symbols_and_constraints() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x", lower=0, upper=1), Symbol(name="y", lower=0, upper=1)],
        sense="max",
        objective={"coeffs": {"x": 1, "y": 2}},
        constraints=[{"name": "c", "coeffs": {"x": 1, "y": 1}, "sense": "<=", "rhs": 1}],
    )
    ops_problem = to_ops_problem(problem)
    assert ops_problem.problem_class == "lp"
    assert ops_problem.sense == "max"
    assert {v.name for v in ops_problem.variables} == {"x", "y"}
    assert ops_problem.constraints[0].name == "c"


def test_compile_linear_optimal_solution() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x", lower=0, upper=1), Symbol(name="y", lower=0, upper=1)],
        sense="min",
        objective={"coeffs": {"x": 1, "y": 1}},
        constraints=[{"name": "cover", "coeffs": {"x": 1, "y": 1}, "sense": ">=", "rhs": 1}],
    )
    result, diagnostics = compile_linear(problem)
    assert result["solver_status"] == "optimal"
    assert result["objective_value"] == pytest.approx(1.0)
    assert diagnostics["converged"] is True


def test_compile_linear_infeasible_reports_issue() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x", lower=0, upper=1)],
        sense="min",
        objective={"coeffs": {"x": 1}},
        constraints=[{"name": "a", "coeffs": {"x": 1}, "sense": ">=", "rhs": 2}],
    )
    result, diagnostics = compile_linear(problem)
    assert result["solver_status"] == "infeasible"
    assert diagnostics["converged"] is False
    assert result["feasibility_issues"]


def test_compile_linear_unbounded_reports_issue() -> None:
    problem = MathProblem(
        symbols=[Symbol(name="x", lower=0, upper=None)],
        sense="min",
        objective={"coeffs": {"x": -1}},
    )
    result, diagnostics = compile_linear(problem)
    assert result["solver_status"] == "unbounded"
    assert diagnostics["converged"] is False
    assert result["feasibility_issues"]


def test_compile_linear_reports_highs_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_unavailable(**kwargs: object) -> None:
        raise HighsNotAvailableError("HiGHS is not installed")

    monkeypatch.setattr("oec.modeling.compile_linear.solve_linear", _raise_unavailable)

    problem = MathProblem(
        symbols=[Symbol(name="x", lower=0, upper=1)],
        objective={"coeffs": {"x": 1}},
    )
    result, diagnostics = compile_linear(problem)
    assert result["solver_status"] == "other"
    assert diagnostics["converged"] is False
