"""W4/W5 experiment builder unit tests (import-safe without running heavy skills)."""

from __future__ import annotations

from oec.evolutionary.contracts import (
    AlgorithmName,
    BudgetSpec,
    EvolutionaryAlgorithmSpec,
)
from oec.experiment.evolutionary import (
    PopulationSpec,
    build_hybrid_training_experiment,
    build_nsga2_experiment,
    build_optimize_single_experiment,
    problem_to_optimize_inputs,
    sphere_problem_2d,
)
from oec.experiment.neural import (
    build_mlp_regressor_experiment,
    build_neural_training_mode_experiment,
    mlp_regressor_inputs,
)
from oec.neural.contracts import DatasetSpec, NeuralModelSpec, TrainingSpec


def _toy_dataset() -> DatasetSpec:
    return DatasetSpec(
        x=[[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]],
        y=[1.0, 3.0, 5.0, 7.0, 9.0, 11.0],
        val_fraction=0.25,
    )


def test_mlp_builder_shape() -> None:
    spec = build_mlp_regressor_experiment(
        dataset=_toy_dataset(),
        experiment_id="w4.mlp",
        seed=7,
        epochs=30,
        hidden_dims=[16, 8],
        lr_scheduler="cosine",
        require_r2_min=0.0,
    )
    assert spec.required_extras == ("neural",)
    assert spec.steps[0].skill_id == "neural.mlp.regressor"
    assert spec.steps[0].inputs["hidden_dims"] == [16, 8]
    assert spec.steps[0].inputs["lr_scheduler"] == "cosine"
    assert spec.metrics[0].path == "result.train_metrics.r_squared"
    assert "train_r2" in spec.validation.metric_min


def test_mlp_inputs_from_contracts() -> None:
    ds = _toy_dataset()
    model = NeuralModelSpec(input_dim=1, hidden_dims=[8], output_dim=1)
    training = TrainingSpec(epochs=12, seed=1)
    inputs = mlp_regressor_inputs(dataset=ds, model=model, training=training)
    assert inputs["epochs"] == 12
    assert inputs["seed"] == 1
    assert len(inputs["x"]) == 6


def test_neural_training_mode_skills() -> None:
    for mode in ("supervised", "gradient", "hybrid", "neuroevolution"):
        spec = build_neural_training_mode_experiment(
            mode=mode,  # type: ignore[arg-type]
            dataset=_toy_dataset(),
            seed=0,
        )
        assert "neural.training" in spec.steps[0].skill_id
        assert "val_fraction" not in spec.steps[0].inputs


def test_population_spec_alias() -> None:
    p = PopulationSpec(generations=10, population=20)
    assert p.generations == 10


def test_optimize_single_builder() -> None:
    problem = sphere_problem_2d()
    algo = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName.PSO,
        budget=BudgetSpec(generations=15, population=16),
        seed=3,
    )
    inputs = problem_to_optimize_inputs(problem, algo)
    assert inputs["algorithm"] == "pso"
    assert inputs["built_in"] == "sphere"
    spec = build_optimize_single_experiment(problem=problem, algorithm=algo, max_objective=0.5)
    assert spec.required_extras == ("evolutionary",)
    assert spec.validation.metric_max["best_objective"] == 0.5
    assert spec.steps[0].skill_id == "evolutionary.optimize_single"


def test_nsga2_and_hybrid_builders() -> None:
    nsga = build_nsga2_experiment(n_var=4, generations=10, population=12, seed=1)
    assert nsga.steps[0].skill_id == "evolutionary.nsga2"
    assert nsga.metrics[0].path == "result.n_nondominated"
    hybrid = build_hybrid_training_experiment(
        x=[[0.0], [1.0], [2.0], [3.0]],
        y=[0.0, 1.0, 2.0, 3.0],
        seed=2,
    )
    assert hybrid.steps[0].skill_id == "neural.training.hybrid"
    assert "neural" in hybrid.required_extras and "evolutionary" in hybrid.required_extras
