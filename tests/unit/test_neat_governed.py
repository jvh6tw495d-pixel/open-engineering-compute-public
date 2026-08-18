"""Governed NEAT contracts, fail-closed extra, and catalog builder (ADR 0044)."""

from __future__ import annotations

import pytest

from oec.evolutionary.contracts import NeatAlgorithmSpec, NeatFitnessName, NeatProblemSpec
from oec.experiment.cross_domain import get_cross_domain_builder, list_cross_domain_builders
from oec.experiment.evolutionary import build_neat_experiment, build_nsga2_experiment
from oec.experiment.specs import ExperimentSpec
from oec.kernel.evolutionary.errors import NeatNotAvailableError


def test_xor_rejects_xy() -> None:
    with pytest.raises(ValueError, match="do not pass x/y"):
        NeatProblemSpec(fitness=NeatFitnessName.XOR, x=[[0.0, 1.0]], y=[1.0])


def test_tabular_requires_xy() -> None:
    with pytest.raises(ValueError, match="requires x and y"):
        NeatProblemSpec(fitness=NeatFitnessName.TABULAR_REGRESSION)


def test_tabular_rejects_nan() -> None:
    with pytest.raises(ValueError, match="finite"):
        NeatProblemSpec(
            fitness=NeatFitnessName.TABULAR_REGRESSION,
            x=[[1.0], [float("nan")]],
            y=[0.0, 1.0],
        )


def test_classification_rejects_fractional_labels() -> None:
    with pytest.raises(ValueError, match="non-negative integers"):
        NeatProblemSpec(
            fitness=NeatFitnessName.TABULAR_CLASSIFICATION,
            x=[[0.0], [1.0]],
            y=[0.0, 0.5],
        )


def test_algorithm_bounds() -> None:
    spec = NeatAlgorithmSpec(generations=8, population=12, seed=3)
    assert spec.feed_forward is True
    with pytest.raises(ValueError):
        NeatAlgorithmSpec(population=3)


def test_fail_closed_when_neat_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "neat", None)
    from oec.kernel.evolutionary import neat as neat_mod

    with pytest.raises(NeatNotAvailableError, match="uv sync --extra evolutionary"):
        neat_mod._require_neat()


def test_builder_on_catalog() -> None:
    rows = {r["name"]: r for r in list_cross_domain_builders()}
    assert rows["build_neat_experiment"]["domains"] == ["evolutionary"]
    assert rows["build_neat_experiment"]["extras"] == ["evolutionary"]
    fn = get_cross_domain_builder("build_neat_experiment")
    assert callable(fn)
    spec = fn(fitness="xor", generations=6, population=10, seed=2)
    assert isinstance(spec, ExperimentSpec)
    assert spec.required_extras == ("evolutionary",)
    assert spec.steps[0].skill_id == "evolutionary.neat"
    assert spec.steps[0].inputs["fitness"] == "xor"


def test_build_neat_tabular_passes_arrays() -> None:
    spec = build_neat_experiment(
        fitness="tabular_regression",
        x=[[0.0], [1.0], [2.0]],
        y=[0.0, 1.0, 2.0],
        generations=5,
        population=8,
        seed=1,
    )
    assert spec.steps[0].inputs["x"] == [[0.0], [1.0], [2.0]]
    assert spec.steps[0].inputs["y"] == [0.0, 1.0, 2.0]


def test_nsga2_builder_passes_fixed_hv_reference() -> None:
    spec = build_nsga2_experiment(n_var=3, generations=4, population=8, hv_reference=[1.2, 1.2])
    assert spec.steps[0].inputs["hv_reference"] == [1.2, 1.2]
