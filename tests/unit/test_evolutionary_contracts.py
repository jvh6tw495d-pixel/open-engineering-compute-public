"""Evolutionary contract unit tests (no pymoo required)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from oec.evolutionary.contracts import (
    AlgorithmName,
    BuiltInProblemName,
    EvolutionaryAlgorithmSpec,
    EvolutionaryProblemSpec,
    VariableSpec,
)
from oec.evolutionary.hashing import problem_fingerprint
from oec.kernel.evolutionary.problems import evaluate_built_in


def test_variable_bounds_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        VariableSpec(name="x", lower=1.0, upper=0.0)


def test_problem_requires_unique_names() -> None:
    with pytest.raises(ValidationError):
        EvolutionaryProblemSpec(
            variables=[
                VariableSpec(name="x", lower=-1, upper=1),
                VariableSpec(name="x", lower=-1, upper=1),
            ]
        )


def test_sphere_minimum_at_origin() -> None:
    import numpy as np

    assert evaluate_built_in(BuiltInProblemName.SPHERE, np.zeros(3)) == 0.0
    assert evaluate_built_in(BuiltInProblemName.SPHERE, np.array([1.0, 0.0])) == 1.0


def test_algorithm_spec_and_fingerprint() -> None:
    algo = EvolutionaryAlgorithmSpec(algorithm=AlgorithmName.PSO, seed=3)
    problem = EvolutionaryProblemSpec(
        variables=[VariableSpec(name="x1", lower=-2, upper=2)],
        built_in=BuiltInProblemName.SPHERE,
    )
    fp = problem_fingerprint(problem.model_dump(mode="json"))
    assert len(fp) == 64
    assert algo.budget.population >= 4
