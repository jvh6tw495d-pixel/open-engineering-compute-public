"""W5 — Evolutionary experiment builders (sugar over ExperimentSpec + evolutionary.*).

Declarative only: maps ``EvolutionaryProblemSpec`` / algorithm contracts into
skill inputs. No arbitrary fitness Python (ADR 0031).

Public builders are discoverable via the fail-closed cross-domain catalog (S4).
NEAT / HyperNEAT remain **excluded** from 3.6 DoD (ADR 0042; deferred since ADR 0037).
"""

from __future__ import annotations

from typing import Any

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
from oec.experiment.specs import (
    ExperimentSpec,
    ExperimentStep,
    MetricDirection,
    MetricSpec,
    ValidationSpec,
)
from oec.experiment.specs import (
    TrainingSpec as ExperimentTrainingSpec,
)

# PopulationSpec is an alias for BudgetSpec (ADR 0035 vocabulary / W5 freeze).
PopulationSpec = BudgetSpec


def problem_to_optimize_inputs(
    problem: EvolutionaryProblemSpec,
    algorithm: EvolutionaryAlgorithmSpec | None = None,
    *,
    seeds: list[int] | None = None,
    history: bool = True,
) -> dict[str, Any]:
    """Map evolutionary contracts → ``evolutionary.optimize_single`` inputs."""
    algorithm = algorithm or EvolutionaryAlgorithmSpec()
    inputs: dict[str, Any] = {
        "variables": [
            {"name": v.name, "lower": v.lower, "upper": v.upper} for v in problem.variables
        ],
        "sense": problem.sense,
        "algorithm": algorithm.algorithm.value
        if isinstance(algorithm.algorithm, AlgorithmName)
        else str(algorithm.algorithm),
        "generations": int(algorithm.budget.generations),
        "population": int(algorithm.budget.population),
        "seed": int(algorithm.seed),
        "history": history,
    }
    if problem.expression is not None:
        inputs["expression"] = problem.expression
    elif problem.built_in is not None:
        bi = problem.built_in
        inputs["built_in"] = bi.value if isinstance(bi, BuiltInProblemName) else str(bi)
    if problem.constraints:
        inputs["constraints"] = list(problem.constraints)
    if seeds:
        inputs["seeds"] = list(seeds)
    return inputs


def build_optimize_single_experiment(
    *,
    problem: EvolutionaryProblemSpec | dict[str, Any],
    algorithm: EvolutionaryAlgorithmSpec | dict[str, Any] | None = None,
    experiment_id: str = "evolutionary.optimize_single",
    seed: int | None = None,
    max_objective: float | None = None,
    title: str | None = None,
    seeds: list[int] | None = None,
) -> ExperimentSpec:
    """Single-objective evolutionary optimization as an ExperimentSpec."""
    if isinstance(problem, dict):
        problem = EvolutionaryProblemSpec.model_validate(problem)
    if algorithm is None:
        algorithm = EvolutionaryAlgorithmSpec(seed=seed if seed is not None else 42)
    elif isinstance(algorithm, dict):
        algorithm = EvolutionaryAlgorithmSpec.model_validate(algorithm)
    if seed is not None:
        algorithm = algorithm.model_copy(update={"seed": seed})

    inputs = problem_to_optimize_inputs(problem, algorithm, seeds=seeds)
    metrics = (
        MetricSpec(
            name="best_objective",
            path="result.best_objective",
            step_id="optimize",
            direction=MetricDirection.MINIMIZE
            if problem.sense == "min"
            else MetricDirection.MAXIMIZE,
        ),
    )
    validation = ValidationSpec()
    if max_objective is not None and problem.sense == "min":
        validation = ValidationSpec(metric_max={"best_objective": float(max_objective)})

    return ExperimentSpec(
        id=experiment_id,
        title=title or "Single-objective evolutionary optimize (W5)",
        seed=int(algorithm.seed),
        required_extras=("evolutionary",),
        training=ExperimentTrainingSpec(
            seed=int(algorithm.seed),
            max_evaluations=int(algorithm.budget.generations * algorithm.budget.population),
            options={
                "algorithm": str(inputs["algorithm"]),
                "population": inputs["population"],
            },
        ),
        metrics=metrics,
        validation=validation,
        steps=(
            ExperimentStep(
                step_id="optimize",
                skill_id="evolutionary.optimize_single",
                inputs=inputs,
            ),
        ),
    )


def build_nsga2_experiment(
    *,
    n_var: int = 5,
    built_in: BuiltInMultiProblemName | str = BuiltInMultiProblemName.ZDT1,
    generations: int = 15,
    population: int = 20,
    seed: int = 0,
    experiment_id: str = "evolutionary.nsga2",
    title: str | None = None,
) -> ExperimentSpec:
    """NSGA-II multi-objective experiment (built-in ZDT-style problems)."""
    bi = (
        built_in
        if isinstance(built_in, BuiltInMultiProblemName)
        else BuiltInMultiProblemName(str(built_in))
    )
    variables = [VariableSpec(name=f"x{i}", lower=0.0, upper=1.0) for i in range(int(n_var))]
    problem = MultiObjectiveProblemSpec(variables=variables, built_in=bi)
    algo = MultiObjectiveAlgorithmSpec(
        algorithm=MultiObjectiveAlgorithmName.NSGA2,
        budget=BudgetSpec(generations=generations, population=population),
        seed=seed,
    )
    inputs: dict[str, Any] = {
        "variables": [
            {"name": v.name, "lower": v.lower, "upper": v.upper} for v in problem.variables
        ],
        "built_in": problem.built_in.value,
        "generations": algo.budget.generations,
        "population": algo.budget.population,
        "seed": algo.seed,
    }
    return ExperimentSpec(
        id=experiment_id,
        title=title or "NSGA-II multi-objective (W5)",
        seed=seed,
        required_extras=("evolutionary",),
        metrics=(
            MetricSpec(
                name="n_nondominated",
                path="result.n_nondominated",
                step_id="nsga2",
                direction=MetricDirection.MAXIMIZE,
            ),
        ),
        steps=(ExperimentStep(step_id="nsga2", skill_id="evolutionary.nsga2", inputs=inputs),),
    )


def build_evo_then_describe_experiment(
    *,
    experiment_id: str = "evolutionary.sphere_then_describe",
    seed: int = 0,
    generations: int = 12,
    population: int = 12,
) -> ExperimentSpec:
    """Demo composition: optimize sphere, then descriptive stats on dummy vector.

    The second step does **not** bind evo solution (skill schemas differ);
    it validates multi-domain sequencing under Experiment Engine.
    """
    problem = EvolutionaryProblemSpec(
        variables=[
            VariableSpec(name="x1", lower=-5.0, upper=5.0),
            VariableSpec(name="x2", lower=-5.0, upper=5.0),
        ],
        built_in=BuiltInProblemName.SPHERE,
    )
    algorithm = EvolutionaryAlgorithmSpec(
        algorithm=AlgorithmName.DIFFERENTIAL_EVOLUTION,
        budget=BudgetSpec(generations=generations, population=population),
        seed=seed,
    )
    evo = build_optimize_single_experiment(
        problem=problem,
        algorithm=algorithm,
        experiment_id=experiment_id,
        seed=seed,
        title="Evo sphere + stats (W5 composition)",
    )
    # Append a second step (rebuild steps)
    steps = list(evo.steps) + [
        ExperimentStep(
            step_id="describe",
            skill_id="statistics.describe",
            inputs={"values": [0.0, 0.1, -0.1, 0.05]},
        )
    ]
    return evo.model_copy(
        update={
            "steps": tuple(steps),
            "metrics": evo.metrics
            + (
                MetricSpec(
                    name="mean",
                    path="result.mean",
                    step_id="describe",
                    direction=MetricDirection.TARGET,
                    target=0.0125,
                    target_abs_tol=0.05,
                ),
            ),
        }
    )


def build_hybrid_training_experiment(
    *,
    x: list[list[float]],
    y: list[float],
    experiment_id: str = "neural.training.hybrid",
    seed: int = 0,
    max_evaluations: int = 6,
    inner_epochs: int = 8,
    epochs: int = 15,
    title: str | None = None,
) -> ExperimentSpec:
    """W4↔W5: hybrid evolutionary + gradient training skill as experiment."""
    return ExperimentSpec(
        id=experiment_id,
        title=title or "Hybrid evo→gradient neural training (W4/W5)",
        seed=seed,
        required_extras=("neural", "evolutionary"),
        metrics=(
            MetricSpec(
                name="seed",
                path="result.seed",
                step_id="hybrid",
                direction=MetricDirection.TARGET,
                target=float(seed),
                target_abs_tol=0.0,
            ),
        ),
        steps=(
            ExperimentStep(
                step_id="hybrid",
                skill_id="neural.training.hybrid",
                inputs={
                    "x": x,
                    "y": y,
                    "seed": seed,
                    "max_evaluations": max_evaluations,
                    "inner_epochs": inner_epochs,
                    "epochs": epochs,
                },
            ),
        ),
    )


# Convenience: sphere box problem
def sphere_problem_2d(
    *,
    lower: float = -5.0,
    upper: float = 5.0,
) -> EvolutionaryProblemSpec:
    return EvolutionaryProblemSpec(
        variables=[
            VariableSpec(name="x1", lower=lower, upper=upper),
            VariableSpec(name="x2", lower=lower, upper=upper),
        ],
        built_in=BuiltInProblemName.SPHERE,
    )
