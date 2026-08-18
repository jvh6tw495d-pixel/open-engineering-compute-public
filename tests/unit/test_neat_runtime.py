"""Live NEAT runtime (requires neat-python via oec[evolutionary])."""

from __future__ import annotations

import pytest

pytest.importorskip("neat")

from oec.evolutionary.contracts import (  # noqa: E402
    NeatAlgorithmSpec,
    NeatFitnessName,
    NeatProblemSpec,
)
from oec.kernel.evolutionary.neat import run_neat  # noqa: E402

pytestmark = pytest.mark.evolutionary


def test_xor_returns_genotype_ir() -> None:
    result = run_neat(
        NeatProblemSpec(fitness=NeatFitnessName.XOR),
        NeatAlgorithmSpec(generations=4, population=10, seed=1),
    )
    assert result.backend == "neat-python"
    assert result.algorithm == "neat"
    assert result.fitness == "xor"
    assert result.n_evaluations >= 10
    assert result.n_generations == 4
    assert result.genotype.n_inputs == 2
    assert result.genotype.n_outputs == 1
    kinds = {node.kind for node in result.genotype.nodes}
    assert "input" in kinds
    assert "output" in kinds
    assert result.n_nodes == len(result.genotype.nodes)
    assert all(isinstance(c.weight, float) for c in result.genotype.connections)


def test_tabular_regression_finite_fitness() -> None:
    result = run_neat(
        NeatProblemSpec(
            fitness=NeatFitnessName.TABULAR_REGRESSION,
            x=[[0.0], [1.0], [2.0], [3.0]],
            y=[0.0, 1.0, 2.0, 3.0],
        ),
        NeatAlgorithmSpec(generations=3, population=8, seed=0),
    )
    assert result.fitness == "tabular_regression"
    assert result.best_fitness <= 0.0
    assert result.genotype.n_inputs == 1
    assert result.genotype.n_outputs == 1


def test_tabular_classification_accuracy() -> None:
    result = run_neat(
        NeatProblemSpec(
            fitness=NeatFitnessName.TABULAR_CLASSIFICATION,
            x=[[0.0], [0.1], [0.9], [1.0]],
            y=[0.0, 0.0, 1.0, 1.0],
        ),
        NeatAlgorithmSpec(generations=3, population=8, seed=2),
    )
    assert result.fitness == "tabular_classification"
    assert 0.0 <= result.best_fitness <= 1.0
