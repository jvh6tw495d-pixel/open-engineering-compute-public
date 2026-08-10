"""Evolutionary search over neural hyperparameters (X2 + ADR 0033 W2).

Delegates to hybrid evolutionary neural training for expanded catalogs.
"""

from __future__ import annotations

from typing import Any

from oec.kernel.neural.evolutionary_training import hybrid_evolutionary_train


def evo_hyperparameter_search(
    x: list[list[float]],
    y: list[float],
    *,
    budget: int = 12,
    seed: int = 42,
    epochs: int = 25,
    device: str = "cpu",
    task: str = "regression",
    max_wall_time_s: float | None = None,
) -> dict[str, Any]:
    """Search MLP hyperparams/architecture with Nevergrad outer + torch inner.

    ``task`` reserved for future classification path; regression today.
    """
    del task  # regression-only in this slice
    result = hybrid_evolutionary_train(
        x,
        y,
        max_evaluations=budget,
        seed=seed,
        inner_epochs=epochs,
        device=device,
        max_wall_time_s=max_wall_time_s,
        facets=["hyperparameters", "architecture"],
    )
    # Back-compat keys for hybrid.evo_hyperparams skill
    best = result.get("best_config") or {}
    return {
        **result,
        "pipeline": "evo_hyperparameter_search→mlp",
        "budget": budget,
        "epochs_per_trial": epochs,
        "best_config": {
            "hidden_dims": best.get("hidden_dims"),
            "lr": best.get("lr"),
            "activation": best.get("activation"),
            "optimizer": best.get("optimizer"),
            "dropout": best.get("dropout"),
            "weight_decay": best.get("weight_decay"),
            "capacity": best.get("capacity"),
        },
        "best_trial_metrics": best,
        "n_trials": result.get("n_trials", 0),
        "trials": result.get("trials", []),
    }
