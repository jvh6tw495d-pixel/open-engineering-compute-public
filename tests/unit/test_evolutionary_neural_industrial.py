"""Industrial gates for ADR 0033 evolutionary neural training."""

from __future__ import annotations

import pytest

pytest.importorskip("torch")
pytest.importorskip("nevergrad")
pytest.importorskip("pymoo")

from oec.kernel.neural.evolutionary_training import (  # noqa: E402
    benchmark_training_strategies,
    hybrid_evolutionary_train,
    multiobjective_neural_search,
    neuroevolution_train,
)

pytestmark = [pytest.mark.neural, pytest.mark.evolutionary]


def _toy() -> tuple[list[list[float]], list[float]]:
    x = [[float(i), float(i % 3)] for i in range(20)]
    y = [2.0 * i + 0.3 * (i % 3) for i in range(20)]
    return x, y


def test_budget_fields_always_present() -> None:
    x, y = _toy()
    out = hybrid_evolutionary_train(x, y, max_evaluations=4, seed=0, inner_epochs=6)
    assert "budget" in out
    assert out["budget"]["max_evaluations"] == 4
    assert "inner_training" in out
    assert out["inner_training"]["max_epochs"] == 6
    assert out["backends"]["outer"] == "nevergrad"
    assert out["backends"]["inner"] == "torch"


def test_fail_closed_neuroevolution_large() -> None:
    x, y = _toy()
    with pytest.raises(ValueError, match="max_params"):
        neuroevolution_train(x, y, hidden=128, max_params=100)


def test_multiseed_outer_mean_std() -> None:
    x, y = _toy()
    out = hybrid_evolutionary_train(
        x,
        y,
        max_evaluations=3,
        seeds=[0, 1],
        inner_epochs=5,
    )
    assert out["mode"] == "hybrid_multiseed"
    assert len(out["seeds"]) == 2
    assert "mean_best_score" in out
    assert "std_best_score" in out
    assert out["budget"]["n_seeds"] == 2


def test_pymoo_multiobjective_pareto() -> None:
    x, y = _toy()
    out = multiobjective_neural_search(
        x,
        y,
        seed=0,
        max_generations=3,
        population_size=4,
        inner_epochs=5,
    )
    assert out["mode"] == "multiobjective_neural_search"
    assert out["backends"]["outer"] == "pymoo"
    assert out["objectives"] == ["rmse", "n_params"]
    assert isinstance(out["pareto_front"], list)
    assert len(out["pareto_front"]) >= 1
    assert "budget" in out


def test_benchmark_three_arms_complete() -> None:
    x, y = _toy()
    out = benchmark_training_strategies(x, y, seed=0, max_evaluations=3, inner_epochs=5)
    strategies = {a["strategy"] for a in out["arms"]}
    assert "gradient_only" in strategies
    assert "hybrid_evolutionary_gradient" in strategies
    assert "neuroevolution_weights" in strategies
    assert "shared_budget" in out
