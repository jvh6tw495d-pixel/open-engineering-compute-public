"""Strong goldens for OEC 3.4 neural + evolutionary compute (P0 quality bar).

These go beyond skill smoke tests: multi-seed reproducibility, hypervolume
presence, MLP overfit, closed GP IR, and method selection policy structure.

Markers:
  - ``evolutionary`` for pymoo/deap paths
  - ``neural`` for torch paths
  - method_select + pure GP IR run without extras (default gate)

Deselected from default pytest via pyproject addopts; run with::

    uv run pytest tests/golden/test_neural_evolutionary_strong.py \\
        -m "neural or evolutionary" -o addopts=
    # or full extras suite:
    uv run pytest -m "neural or evolutionary" -o addopts= \\
        --import-mode=importlib
"""

from __future__ import annotations

import pytest

from oec.kernel.evolutionary.gp_operators import ALLOWED_OP_NAMES, eval_tree
from oec.kernel.scientific.method_select import select_method

# ---------------------------------------------------------------------------
# Always-on (no extras): GP IR closed set + method_select structure
# ---------------------------------------------------------------------------


def test_gp_ir_poly2_identity_and_closed_ops() -> None:
    """Closed IR evaluates x^2 + 0.5x + 0.1; forbidden ops raise."""
    # y = x0^2 + 0.5*x0 + 0.1
    tree = {
        "op": "add",
        "args": [
            {
                "op": "add",
                "args": [
                    {"op": "mul", "args": [{"var": "x0"}, {"var": "x0"}]},
                    {"op": "mul", "args": [{"const": 0.5}, {"var": "x0"}]},
                ],
            },
            {"const": 0.1},
        ],
    }
    for x in (-1.5, -0.5, 0.0, 0.75, 2.0):
        expected = x * x + 0.5 * x + 0.1
        got = eval_tree(tree, {"x0": x})
        assert abs(got - expected) < 1e-12

    assert "add" in ALLOWED_OP_NAMES
    with pytest.raises(ValueError, match="not in allow-list"):
        eval_tree({"op": "eval", "args": [{"const": 1.0}]}, {})
    with pytest.raises(ValueError, match="not in allow-list"):
        eval_tree({"op": "__import__", "args": [{"const": 1.0}]}, {})


def test_method_select_catalog_and_policy() -> None:
    """X3 returns structured selection + agent-must-execute policy for all classes."""
    classes = (
        "soo_box",
        "multiobjective",
        "symbolic_regression",
        "blackbox",
        "neural_tabular",
        "neural_sequence",
        "neural_graph",
        "hybrid_surrogate",
        "hyperparam_search",
    )
    for pc in classes:
        out = select_method(problem_class=pc, run_probe_benchmark=False)
        assert out["problem_class"] == pc
        assert "available_candidates" in out
        assert "unavailable_candidates" in out
        assert "selected" in out
        assert "policy" in out
        assert "ExecutionResult" in out["policy"]
        assert "skill_id" in out["policy"] or "skill" in out["policy"].lower()
        assert out["message"] in ("ok", "no_available_method")
        assert len(out["problem_fingerprint"]) == 64


# ---------------------------------------------------------------------------
# Evolutionary (pymoo / deap)
# ---------------------------------------------------------------------------


@pytest.mark.evolutionary
def test_sphere_multi_seed_reproducible_and_near_origin() -> None:
    """Same seed → identical best_objective; different seed still near origin."""
    pytest.importorskip("pymoo")
    from oec.evolutionary.contracts import (
        AlgorithmName,
        BudgetSpec,
        BuiltInProblemName,
        EvolutionaryAlgorithmSpec,
        EvolutionaryProblemSpec,
        VariableSpec,
    )
    from oec.kernel.evolutionary.optimize import optimize_single

    problem = EvolutionaryProblemSpec(
        variables=[
            VariableSpec(name="x1", lower=-2.0, upper=2.0),
            VariableSpec(name="x2", lower=-2.0, upper=2.0),
            VariableSpec(name="x3", lower=-2.0, upper=2.0),
        ],
        built_in=BuiltInProblemName.SPHERE,
    )
    budget = BudgetSpec(generations=30, population=24)

    r0a = optimize_single(
        problem,
        EvolutionaryAlgorithmSpec(
            algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
            budget=budget,
            seed=0,
        ),
    )
    r0b = optimize_single(
        problem,
        EvolutionaryAlgorithmSpec(
            algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
            budget=budget,
            seed=0,
        ),
    )
    r1 = optimize_single(
        problem,
        EvolutionaryAlgorithmSpec(
            algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
            budget=budget,
            seed=1,
        ),
    )

    assert r0a.backend == "pymoo"
    assert r0a.best_objective == r0b.best_objective
    assert r0a.best_x == r0b.best_x
    assert r0a.best_objective < 0.05
    assert r1.best_objective < 0.05
    # Seeds should not be forced identical across different seeds (weak check)
    assert r0a.seed == 0 and r1.seed == 1


@pytest.mark.evolutionary
def test_zdt1_nsga2_has_positive_hypervolume() -> None:
    """NSGA-II on ZDT1 returns a non-empty non-dominated set with HV > 0."""
    pytest.importorskip("pymoo")
    from oec.evolutionary.contracts import (
        BudgetSpec,
        BuiltInMultiProblemName,
        MultiObjectiveAlgorithmName,
        MultiObjectiveAlgorithmSpec,
        MultiObjectiveProblemSpec,
        VariableSpec,
    )
    from oec.kernel.evolutionary.multiobjective import optimize_multi

    problem = MultiObjectiveProblemSpec(
        variables=[VariableSpec(name=f"x{i}", lower=0.0, upper=1.0) for i in range(5)],
        built_in=BuiltInMultiProblemName.ZDT1,
        n_objectives=2,
    )
    algo = MultiObjectiveAlgorithmSpec(
        algorithm=MultiObjectiveAlgorithmName.NSGA2,
        budget=BudgetSpec(generations=40, population=40),
        seed=7,
    )
    res = optimize_multi(problem, algo)
    assert res.backend == "pymoo"
    assert res.n_nondominated >= 5
    assert res.hypervolume is not None
    assert res.hypervolume > 0.0
    assert all(len(f) == 2 for f in res.objective_vectors)


@pytest.mark.evolutionary
def test_gp_poly2_tree_ir_is_evaluable() -> None:
    """DEAP GP returns best_tree_ir that eval_tree can score on the target."""
    pytest.importorskip("deap")
    from oec.kernel.evolutionary.gp import run_genetic_programming

    out = run_genetic_programming(
        target="poly2",
        n_var=1,
        n_samples=40,
        population=50,
        generations=15,
        max_depth=4,
        seed=0,
    )
    assert out["backend"] == "deap"
    assert "best_tree_ir" in out
    tree = out["best_tree_ir"]
    # IR must evaluate without raising for a few points
    for x in (-1.0, 0.0, 1.0):
        val = eval_tree(tree, {"x0": float(x)})
        assert isinstance(val, float)
        assert val == val  # not NaN
    assert out["best_mse"] < 50.0


# ---------------------------------------------------------------------------
# Neural (torch)
# ---------------------------------------------------------------------------


@pytest.mark.neural
def test_mlp_linear_overfit_r2() -> None:
    """MLP regressor overfits y = 2x + 1 with R² > 0.95 (train, no val split)."""
    pytest.importorskip("torch")
    from oec.kernel.neural.training import train_mlp
    from oec.neural.contracts import (
        DatasetSpec,
        NeuralModelSpec,
        OptimizerName,
        OptimizerSpec,
        TrainingSpec,
    )

    x = [[float(i)] for i in range(16)]
    y = [2.0 * i + 1.0 for i in range(16)]
    dataset = DatasetSpec(x=x, y=y, val_fraction=0.0)
    model = NeuralModelSpec(input_dim=1, hidden_dims=[32, 16], output_dim=1)
    training = TrainingSpec(
        epochs=120,
        seed=0,
        normalize_x=True,
        early_stopping_patience=None,
        optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=0.05),
    )
    result = train_mlp(dataset, model, training)
    assert result.backend == "torch"
    r2 = result.train_metrics["r_squared"]
    assert r2 > 0.95, f"expected R²>0.95, got {r2}"
    assert "checkpoint" in result.model_dump()
    assert result.epochs_ran >= 1
