"""Part B evolutionary depth: expression IR, constraints, multi-seed, HV ref."""

from __future__ import annotations

import pytest

from oec.evolutionary.contracts import (
    AlgorithmName,
    BudgetSpec,
    BuiltInMultiProblemName,
    BuiltInProblemName,
    EvolutionaryAlgorithmSpec,
    EvolutionaryProblemSpec,
    MultiObjectiveAlgorithmName,
    MultiObjectiveAlgorithmSpec,
    MultiObjectiveProblemSpec,
    VariableSpec,
)
from oec.evolutionary.runtime import EvolutionaryRuntimeSpec
from oec.kernel.evolutionary.expression import evaluate_expression

pytestmark = pytest.mark.evolutionary


def test_expression_sphere_ir_no_pymoo() -> None:
    # f = x1^2 + x2^2
    tree = {
        "op": "add",
        "args": [
            {"op": "mul", "args": [{"var": "x1"}, {"var": "x1"}]},
            {"op": "mul", "args": [{"var": "x2"}, {"var": "x2"}]},
        ],
    }
    import numpy as np

    assert evaluate_expression(tree, ["x1", "x2"], np.array([1.0, 2.0])) == 5.0


def test_problem_spec_expression_or_builtin() -> None:
    vars_ = [VariableSpec(name="x1", lower=-1, upper=1)]
    with pytest.raises(ValueError, match="built_in or expression"):
        EvolutionaryProblemSpec(variables=vars_, built_in=None, expression=None)
    p = EvolutionaryProblemSpec(
        variables=vars_,
        built_in=None,
        expression={"op": "mul", "args": [{"var": "x1"}, {"var": "x1"}]},
    )
    assert p.expression is not None


@pytest.mark.evolutionary
def test_optimize_expression_near_origin() -> None:
    pytest.importorskip("pymoo")
    from oec.kernel.evolutionary.optimize import optimize_single

    # minimize (x-1)^2 via expression IR → optimum at x=1
    tree = {
        "op": "mul",
        "args": [
            {"op": "sub", "args": [{"var": "x"}, {"const": 1.0}]},
            {"op": "sub", "args": [{"var": "x"}, {"const": 1.0}]},
        ],
    }
    problem = EvolutionaryProblemSpec(
        variables=[VariableSpec(name="x", lower=-2.0, upper=2.0)],
        built_in=None,
        expression=tree,
    )
    algo = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
        budget=BudgetSpec(generations=25, population=20),
        seed=0,
    )
    res = optimize_single(problem, algo)
    assert res.objective_mode == "expression"
    assert res.best_objective < 0.05
    assert abs(res.best_x["x"] - 1.0) < 0.2


@pytest.mark.evolutionary
def test_optimize_with_inequality_constraint() -> None:
    pytest.importorskip("pymoo")
    from oec.kernel.evolutionary.optimize import optimize_single

    # minimize sphere with x1 + x2 >= 1  →  g = 1 - x1 - x2 <= 0
    problem = EvolutionaryProblemSpec(
        variables=[
            VariableSpec(name="x1", lower=0.0, upper=1.0),
            VariableSpec(name="x2", lower=0.0, upper=1.0),
        ],
        built_in=BuiltInProblemName.SPHERE,
        constraints=[
            {
                "name": "sum_ge_1",
                "tree": {
                    "op": "sub",
                    "args": [
                        {"const": 1.0},
                        {
                            "op": "add",
                            "args": [{"var": "x1"}, {"var": "x2"}],
                        },
                    ],
                },
            }
        ],
    )
    algo = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
        budget=BudgetSpec(generations=30, population=24),
        seed=1,
    )
    res = optimize_single(problem, algo)
    assert res.n_constraints == 1
    assert res.best_x["x1"] + res.best_x["x2"] >= 0.9


@pytest.mark.evolutionary
def test_seed_matrix_mean_std() -> None:
    pytest.importorskip("pymoo")
    from oec.kernel.evolutionary.seed_matrix import run_seed_matrix

    problem = EvolutionaryProblemSpec(
        variables=[
            VariableSpec(name="x1", lower=-2, upper=2),
            VariableSpec(name="x2", lower=-2, upper=2),
        ],
        built_in=BuiltInProblemName.SPHERE,
    )
    algo = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
        budget=BudgetSpec(generations=15, population=16),
        seed=0,
    )
    rt = EvolutionaryRuntimeSpec(
        seeds=[0, 1, 2],
        budget=BudgetSpec(generations=15, population=16),
    )
    report = run_seed_matrix(problem, algo, rt)
    assert len(report.seeds) == 3
    assert len(report.best_objectives) == 3
    assert report.mean_best_objective < 0.5
    assert report.std_best_objective >= 0.0


@pytest.mark.evolutionary
def test_multi_hv_fixed_reference() -> None:
    pytest.importorskip("pymoo")
    from oec.kernel.evolutionary.multiobjective import optimize_multi

    problem = MultiObjectiveProblemSpec(
        variables=[VariableSpec(name=f"x{i}", lower=0.0, upper=1.0) for i in range(3)],
        built_in=BuiltInMultiProblemName.ZDT1,
        n_objectives=2,
    )
    algo = MultiObjectiveAlgorithmSpec(
        algorithm=MultiObjectiveAlgorithmName.NSGA2,
        budget=BudgetSpec(generations=20, population=24),
        seed=3,
    )
    rt = EvolutionaryRuntimeSpec(seed=3, hv_reference=[1.1, 1.1])
    res = optimize_multi(problem, algo, runtime=rt)
    assert res.hv_reference == [1.1, 1.1]
    assert res.hypervolume is not None
    assert res.hypervolume >= 0.0
    assert res.runtime is not None
    assert res.runtime["hv_reference_mode"] == "fixed"
