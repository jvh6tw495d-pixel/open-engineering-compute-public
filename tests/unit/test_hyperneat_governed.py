"""Governed HyperNEAT contracts, catalog, and fail-closed extra (ADR 0045)."""

from __future__ import annotations

import pytest

from oec.evolutionary.contracts import (
    HyperNeatAlgorithmSpec,
    HyperNeatSubstrateName,
    NeatFitnessName,
    NeatProblemSpec,
)
from oec.experiment.cross_domain import get_cross_domain_builder, list_cross_domain_builders
from oec.experiment.evolutionary import build_hyperneat_experiment
from oec.experiment.specs import ExperimentSpec
from oec.kernel.evolutionary.errors import NeatNotAvailableError


def test_xor_rejects_xy() -> None:
    with pytest.raises(ValueError, match="do not pass x/y"):
        NeatProblemSpec(fitness=NeatFitnessName.XOR, x=[[0.0, 1.0]], y=[1.0])


def test_algorithm_defaults() -> None:
    spec = HyperNeatAlgorithmSpec()
    assert spec.substrate is HyperNeatSubstrateName.LAYERED_1D
    assert spec.hidden_layers == 1
    with pytest.raises(ValueError):
        HyperNeatAlgorithmSpec(hidden_layers=3)


def test_es_quadtree_is_a_closed_substrate() -> None:
    spec = HyperNeatAlgorithmSpec(substrate=HyperNeatSubstrateName.ES_QUADTREE, es_max_depth=2)
    assert spec.substrate is HyperNeatSubstrateName.ES_QUADTREE
    assert spec.es_max_hidden == 16
    assert spec.es_band_threshold == 0.3
    assert spec.es_max_iteration == 1
    assert spec.feed_forward is True


def test_fail_closed_when_neat_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "neat", None)
    from oec.kernel.evolutionary import hyperneat as hn

    with pytest.raises(NeatNotAvailableError, match="uv sync --extra evolutionary"):
        hn._require_neat()


def test_builder_on_catalog() -> None:
    rows = {r["name"]: r for r in list_cross_domain_builders()}
    assert rows["build_hyperneat_experiment"]["extras"] == ["evolutionary"]
    fn = get_cross_domain_builder("build_hyperneat_experiment")
    assert callable(fn)
    spec = fn(fitness="xor", generations=4, population=8, seed=1)
    assert isinstance(spec, ExperimentSpec)
    assert spec.steps[0].skill_id == "evolutionary.hyperneat"
    assert spec.steps[0].inputs["substrate"] == "layered_1d"


@pytest.mark.evolutionary
def test_es_quadtree_xor_runs() -> None:
    pytest.importorskip("neat")
    from oec.kernel.evolutionary.hyperneat import run_hyperneat

    result = run_hyperneat(
        NeatProblemSpec(fitness=NeatFitnessName.XOR),
        HyperNeatAlgorithmSpec(
            substrate=HyperNeatSubstrateName.ES_QUADTREE,
            generations=2,
            population=6,
            seed=1,
            es_max_depth=2,
            es_max_hidden=8,
        ),
    )
    assert result.algorithm == "es_hyperneat"
    assert result.substrate.name == "es_quadtree"
    assert result.substrate.kind == "es_hyperneat"
    assert result.substrate.extraction == "gauci_quadtree"
    assert result.substrate.hidden_layers is None
    assert result.substrate.hidden_width is None
    assert result.substrate.max_depth == 2
    assert result.substrate.band_threshold == 0.3
    assert result.cppn.n_inputs == 4
    assert result.cppn.feed_forward is True


def test_builder_can_select_es_quadtree() -> None:
    spec = build_hyperneat_experiment(fitness="xor", substrate="es_quadtree", generations=2)
    assert spec.steps[0].inputs["substrate"] == "es_quadtree"
    assert spec.steps[0].inputs["es_max_depth"] == 3
    assert spec.steps[0].inputs["es_band_threshold"] == 0.3
    assert spec.steps[0].inputs["es_max_iteration"] == 1


def test_build_hyperneat_tabular_passes_arrays() -> None:
    spec = build_hyperneat_experiment(
        fitness="tabular_regression",
        x=[[0.0], [1.0]],
        y=[0.0, 1.0],
        generations=3,
        population=6,
        seed=0,
    )
    assert spec.steps[0].inputs["x"] == [[0.0], [1.0]]
