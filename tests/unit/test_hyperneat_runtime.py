"""Live HyperNEAT runtime (requires neat-python)."""

from __future__ import annotations

import pytest

pytest.importorskip("neat")

from oec.evolutionary.contracts import (  # noqa: E402
    HyperNeatAlgorithmSpec,
    NeatFitnessName,
    NeatProblemSpec,
)
from oec.kernel.evolutionary.hyperneat import run_hyperneat  # noqa: E402

pytestmark = pytest.mark.evolutionary


def test_xor_returns_cppn_and_substrate() -> None:
    result = run_hyperneat(
        NeatProblemSpec(fitness=NeatFitnessName.XOR),
        HyperNeatAlgorithmSpec(generations=3, population=8, seed=1),
    )
    assert result.backend == "neat-python"
    assert result.algorithm == "hyperneat"
    assert result.cppn.n_inputs == 4
    assert result.cppn.n_outputs == 1
    assert result.substrate.name == "layered_1d"
    assert result.substrate.n_inputs == 2
    assert result.substrate.n_outputs == 1
    kinds = {node.kind for node in result.substrate.nodes}
    assert kinds == {"input", "hidden", "output"}
    assert result.n_evaluations >= 8
    assert result.n_generations == 3


def test_tabular_regression_finite() -> None:
    result = run_hyperneat(
        NeatProblemSpec(
            fitness=NeatFitnessName.TABULAR_REGRESSION,
            x=[[0.0], [1.0], [2.0]],
            y=[0.0, 1.0, 2.0],
        ),
        HyperNeatAlgorithmSpec(generations=2, population=6, seed=0, hidden_layers=0),
    )
    assert result.fitness == "tabular_regression"
    assert result.best_fitness <= 0.0
    assert result.substrate.n_inputs == 1
    assert result.substrate.hidden_layers == 0
