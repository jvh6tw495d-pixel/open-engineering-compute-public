"""Strong goldens for OEC 3.4 neural + evolutionary compute (P0 quality bar).

These go beyond skill smoke tests: multi-seed reproducibility, hypervolume
quality, MLP overfit, closed GP IR, and method selection structure.

Markers:
  - ``evolutionary`` for pymoo/deap paths (deselected by default addopts)
  - ``neural`` for torch paths (deselected by default addopts)
  - Unmarked tests (GP IR closed ops + method_select structure) run on the
    default PR gate

Run extras-only suite::

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

    # Core arithmetic + at least one unary from the closed set
    assert {"add", "mul", "sub", "div"}.issubset(ALLOWED_OP_NAMES)
    assert "sin" in ALLOWED_OP_NAMES
    with pytest.raises(ValueError, match="not in allow-list"):
        eval_tree({"op": "eval", "args": [{"const": 1.0}]}, {})
    with pytest.raises(ValueError, match="not in allow-list"):
        eval_tree({"op": "__import__", "args": [{"const": 1.0}]}, {})
    with pytest.raises(ValueError, match="not in allow-list"):
        eval_tree({"op": "exec", "args": [{"const": 1.0}]}, {})


def test_method_select_catalog_structure() -> None:
    """X3 returns structured selection for all problem classes (catalog only).

    Authority (run_id / invented numbers) is enforced in agents, not by
    substring-matching the static policy blurb.
    """
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
        assert isinstance(out["available_candidates"], list)
        assert isinstance(out["unavailable_candidates"], list)
        assert "selected" in out
        assert "policy" in out and isinstance(out["policy"], str) and out["policy"]
        assert out["message"] in ("ok", "no_available_method")
        assert len(out["problem_fingerprint"]) == 64
        # Selected entry (when present) must name a skill
        if out["selected"] is not None:
            assert "skill_id" in out["selected"]
            assert out["selected"]["skill_id"]


# ---------------------------------------------------------------------------
# Evolutionary (pymoo / deap)
# ---------------------------------------------------------------------------


@pytest.mark.evolutionary
def test_sphere_multi_seed_reproducible_and_near_origin() -> None:
    """Same seed → identical solution; different seed still near origin and differs."""
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
    assert r0a.seed == 0 and r1.seed == 1
    # Cross-seed diversity: solutions (or objectives) must not be bit-identical
    assert r0a.best_x != r1.best_x or r0a.best_objective != r1.best_objective


@pytest.mark.evolutionary
def test_zdt1_nsga2_front_quality() -> None:
    """NSGA-II on ZDT1: non-empty front, HV floor, near-axis f1, objective spread."""
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
    # Same-seed reproducibility of HV / nondominated count
    res2 = optimize_multi(problem, algo)

    assert res.backend == "pymoo"
    assert res.n_nondominated >= 10
    assert res.hypervolume is not None
    # Empirical floor under seed=7 / 40×40 (observed ~0.11); not tautological HV>0
    assert res.hypervolume >= 0.05, f"HV too small: {res.hypervolume}"
    assert res.hypervolume == res2.hypervolume
    assert res.n_nondominated == res2.n_nondominated

    nd = [f for f, mask in zip(res.objective_vectors, res.nondominated_mask, strict=True) if mask]
    assert nd
    f1s = [p[0] for p in nd]
    assert min(f1s) < 0.05, f"front should approach f1≈0, min_f1={min(f1s)}"
    assert max(f1s) - min(f1s) > 0.3, "front should cover meaningful f1 range"
    assert all(len(f) == 2 for f in res.objective_vectors)


@pytest.mark.evolutionary
def test_gp_poly2_tree_ir_is_evaluable() -> None:
    """DEAP GP returns evaluable IR with training MSE < 1 and holdout fidelity."""
    pytest.importorskip("deap")
    import numpy as np

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
    # Training MSE floor (seed=0 observed ~0.36)
    assert out["best_mse"] < 1.0, f"best_mse too high: {out['best_mse']}"
    # Hold-out score against known poly2 target
    rng = np.random.default_rng(99)
    xs = rng.uniform(-2.0, 2.0, size=30)
    se = [
        (float(x) ** 2 + 0.5 * float(x) + 0.1 - eval_tree(tree, {"x0": float(x)})) ** 2 for x in xs
    ]
    holdout_mse = float(np.mean(se))
    assert holdout_mse < 5.0, f"holdout_mse too high: {holdout_mse}"


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
