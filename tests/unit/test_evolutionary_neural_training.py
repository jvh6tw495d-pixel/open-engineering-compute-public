"""ADR 0033 evolutionary neural training modes (requires torch + nevergrad)."""

from __future__ import annotations

import pytest

pytest.importorskip("torch")
pytest.importorskip("nevergrad")

from oec.kernel.neural.evolutionary_training import (  # noqa: E402
    benchmark_training_strategies,
    hybrid_evolutionary_train,
    neuroevolution_train,
    search_architecture,
    search_features,
    search_policy,
)

pytestmark = [pytest.mark.neural, pytest.mark.evolutionary]


def _toy() -> tuple[list[list[float]], list[float]]:
    x = [[float(i), float(i % 3)] for i in range(24)]
    y = [2.0 * i + 0.5 * (i % 3) for i in range(24)]
    return x, y


def test_hybrid_evolutionary_train() -> None:
    x, y = _toy()
    out = hybrid_evolutionary_train(
        x,
        y,
        max_evaluations=6,
        seed=0,
        inner_epochs=10,
        facets=["hyperparameters", "architecture"],
    )
    assert out["mode"] == "hybrid"
    assert out["n_trials"] >= 1
    assert out["best_config"] is not None
    assert "pareto_front" in out
    assert out["budget"]["max_evaluations"] == 6


def test_neuroevolution_small() -> None:
    x, y = _toy()
    out = neuroevolution_train(x, y, max_evaluations=15, seed=1, hidden=4, max_params=200)
    assert out["mode"] == "neuroevolution"
    assert out["best_mse"] is not None
    assert out["n_params"] <= 200


def test_neuroevolution_rejects_large() -> None:
    x, y = _toy()
    with pytest.raises(ValueError, match="max_params"):
        neuroevolution_train(x, y, hidden=64, max_params=50)


def test_search_architecture_pareto() -> None:
    x, y = _toy()
    out = search_architecture(x, y, max_evaluations=5, seed=0, inner_epochs=8)
    assert isinstance(out.get("pareto_front"), list)


def test_search_features_and_policy() -> None:
    x, y = _toy()
    f = search_features(x, y, max_evaluations=4, seed=2, inner_epochs=6)
    assert f["n_trials"] >= 1
    p = search_policy(x, y, max_evaluations=4, seed=3, inner_epochs=6)
    assert p["n_trials"] >= 1


def test_benchmark_three_arms() -> None:
    x, y = _toy()
    out = benchmark_training_strategies(x, y, seed=0, max_evaluations=4, inner_epochs=8)
    arms = {a["strategy"] for a in out["arms"]}
    assert "gradient_only" in arms
    assert "hybrid_evolutionary_gradient" in arms
