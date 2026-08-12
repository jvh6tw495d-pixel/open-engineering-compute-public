"""W4/W5 live experiment runs (requires oec[neural] + oec[evolutionary])."""

from __future__ import annotations

import pytest

from oec.evolutionary.contracts import (
    AlgorithmName,
    BudgetSpec,
    EvolutionaryAlgorithmSpec,
)
from oec.experiment import ExperimentStatus
from oec.experiment.evolutionary import (
    build_hybrid_training_experiment,
    build_nsga2_experiment,
    build_optimize_single_experiment,
    sphere_problem_2d,
)
from oec.experiment.neural import build_mlp_regressor_experiment
from oec.neural.contracts import DatasetSpec
from oec.sdk import Engine

torch = pytest.importorskip("torch")
pymoo = pytest.importorskip("pymoo")
del torch, pymoo


def _engine() -> Engine:
    return Engine(skills_root="skills")


def test_w4_mlp_regressor_experiment() -> None:
    ds = DatasetSpec(
        x=[[float(i)] for i in range(12)],
        y=[2.0 * float(i) + 1.0 for i in range(12)],
        val_fraction=0.25,
    )
    spec = build_mlp_regressor_experiment(
        dataset=ds,
        experiment_id="w4_mlp_live",
        seed=0,
        epochs=40,
        hidden_dims=[16],
        lr=0.05,
        device="cpu",
    )
    record = _engine().run_experiment(spec)
    assert record.status == ExperimentStatus.COMPLETED
    assert record.metrics[0].value is not None
    assert record.steps[0].execution is not None
    assert "checkpoint" in record.steps[0].execution.result


def test_w5_sphere_optimize_experiment() -> None:
    algo = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
        budget=BudgetSpec(generations=12, population=12),
        seed=0,
    )
    spec = build_optimize_single_experiment(
        problem=sphere_problem_2d(),
        algorithm=algo,
        experiment_id="w5_sphere_live",
        max_objective=0.5,
    )
    record = _engine().run_experiment(spec)
    assert record.status == ExperimentStatus.COMPLETED
    assert record.metrics[0].value is not None
    assert record.metrics[0].value <= 0.5


def test_w5_nsga2_experiment() -> None:
    spec = build_nsga2_experiment(
        n_var=5, generations=8, population=12, seed=0, experiment_id="w5_nsga_live"
    )
    record = _engine().run_experiment(spec)
    assert record.status == ExperimentStatus.COMPLETED
    assert record.metrics[0].value is not None
    assert record.metrics[0].value >= 1.0


def test_w4_w5_hybrid_training_experiment() -> None:
    x = [[float(i)] for i in range(12)]
    y = [2.0 * float(i) + 1.0 for i in range(12)]
    spec = build_hybrid_training_experiment(
        x=x,
        y=y,
        seed=0,
        max_evaluations=4,
        inner_epochs=5,
        epochs=10,
        experiment_id="w45_hybrid_live",
    )
    record = _engine().run_experiment(spec)
    assert record.status == ExperimentStatus.COMPLETED
    assert record.steps[0].execution is not None
    assert record.steps[0].execution.result.get("mode") is not None
