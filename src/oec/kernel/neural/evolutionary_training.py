"""Evolutionary neural training modes (ADR 0033): hybrid, neuroevolution, search, benchmark.

Merit: PyTorch (inner train) + Nevergrad (HPO / weight evo) + pymoo (NSGA multi-obj).
DEAP structural genotype is residual polish (not this module). No agent Python.
"""

from __future__ import annotations

import time
from typing import Any, Literal

import numpy as np

from oec.evolutionary.hashing import problem_fingerprint
from oec.kernel.evolutionary.errors import NevergradNotAvailableError, PymooNotAvailableError
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import train_mlp
from oec.neural.contracts import (
    ActivationName,
    DatasetSpec,
    DeviceSpec,
    LossName,
    NeuralModelSpec,
    NeuralTask,
    OptimizerName,
    OptimizerSpec,
    TrainingSpec,
)
from oec.neural.runtime import resolve_capacity

SearchFacet = Literal[
    "hyperparameters",
    "architecture",
    "features",
    "loss_weights",
    "policy",
    "hybrid",
]


def _require_nevergrad() -> Any:
    try:
        import nevergrad as ng
    except ImportError as exc:
        raise NevergradNotAvailableError(
            "nevergrad is not installed. Install with: uv sync --extra evolutionary"
        ) from exc
    return ng


def _device(device: str) -> DeviceSpec:
    from typing import Literal, cast

    allowed: set[str] = {"cpu", "cuda", "auto"}
    d = device if device in allowed else "cpu"
    return DeviceSpec(device=cast(Literal["cpu", "cuda", "auto"], d))


def _split_xy(
    x: list[list[float]], y: list[float], val_fraction: float, seed: int
) -> tuple[list[list[float]], list[float], list[list[float]], list[float]]:
    n = len(x)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_val = int(round(n * val_fraction)) if val_fraction > 0 else 0
    if n_val <= 0 or n_val >= n:
        return x, y, [], []
    val_idx, train_idx = idx[:n_val], idx[n_val:]
    xt = [x[i] for i in train_idx]
    yt = [y[i] for i in train_idx]
    xv = [x[i] for i in val_idx]
    yv = [y[i] for i in val_idx]
    return xt, yt, xv, yv


def _apply_feature_mask(x: list[list[float]], mask: list[bool]) -> list[list[float]]:
    return [[row[j] for j, m in enumerate(mask) if m] for row in x]


def _train_candidate(
    x: list[list[float]],
    y: list[float],
    *,
    hidden_dims: list[int],
    activation: ActivationName,
    lr: float,
    weight_decay: float,
    dropout: float,
    optimizer: OptimizerName,
    momentum: float,
    epochs: int,
    batch_size: int,
    seed: int,
    device: str,
    val_fraction: float,
    loss: LossName = LossName.MSE,
    loss_weights: dict[str, float] | None = None,
    early_stopping_patience: int | None = 5,
    feature_mask: list[bool] | None = None,
) -> dict[str, Any]:
    """Inner gradient training for one evolutionary candidate."""
    x_use = _apply_feature_mask(x, feature_mask) if feature_mask is not None else x
    if feature_mask is not None and not any(feature_mask):
        return {"score": 1e6, "error": "empty_feature_mask"}

    # Weighted loss: mix MSE/MAE via LossName only (closed); lambdas recorded
    lw = loss_weights or {"mse": 1.0}
    primary = LossName.HUBER if lw.get("huber", 0) > lw.get("mse", 0) else loss

    try:
        result = train_mlp(
            DatasetSpec(x=x_use, y=y, val_fraction=val_fraction),
            NeuralModelSpec(
                architecture="mlp",
                input_dim=len(x_use[0]),
                output_dim=1,
                hidden_dims=list(hidden_dims),
                activation=activation,
                dropout=dropout,
            ),
            TrainingSpec(
                task=NeuralTask.REGRESSION,
                epochs=epochs,
                batch_size=batch_size,
                loss=primary,
                optimizer=OptimizerSpec(
                    name=optimizer, lr=lr, weight_decay=weight_decay, momentum=momentum
                ),
                seed=seed,
                device=_device(device),
                normalize_x=True,
                early_stopping_patience=early_stopping_patience,
            ),
        )
    except TorchNotAvailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        return {"score": 1e6, "error": str(exc)}

    metrics = result.val_metrics or result.train_metrics
    rmse = float(metrics.get("rmse", 1e3))
    r2 = float(metrics.get("r_squared", -1.0))
    mae = float(metrics.get("mae", rmse))
    # Combined score with optional loss weights (lower is better)
    score = (
        float(lw.get("mse", 1.0)) * rmse
        + float(lw.get("mae", 0.0)) * mae
        + float(lw.get("size", 0.0)) * (result.n_params or 0) / 1e5
    )
    return {
        "score": score,
        "rmse": rmse,
        "mae": mae,
        "r_squared": r2,
        "n_params": result.n_params,
        "epochs_ran": result.epochs_ran,
        "hidden_dims": list(hidden_dims),
        "activation": activation.value,
        "lr": lr,
        "weight_decay": weight_decay,
        "dropout": dropout,
        "optimizer": optimizer.value,
        "momentum": momentum,
        "batch_size": batch_size,
        "loss_weights": lw,
        "feature_mask": feature_mask,
        "primary_loss": primary.value,
    }


def hybrid_evolutionary_train(
    x: list[list[float]],
    y: list[float],
    *,
    max_evaluations: int = 16,
    max_generations: int | None = None,
    population_size: int = 8,
    max_wall_time_s: float | None = None,
    seed: int = 42,
    seeds: list[int] | None = None,
    inner_epochs: int = 20,
    early_stopping_patience: int = 5,
    device: str = "cpu",
    val_fraction: float = 0.25,
    facets: list[str] | None = None,
    multiobjective: bool = False,
) -> dict[str, Any]:
    """Hybrid: evolutionary outer search → PyTorch train → fitness (ADR 0033 W3).

    Default facets: hyperparameters + architecture (capacity). Optional features,
    loss_weights, policy when listed in ``facets``.

    When ``seeds`` has more than one value, runs the full hybrid loop per seed
    and aggregates mean/std of best scores (industrial multi-seed outer).
    When ``multiobjective`` is True, uses pymoo NSGA-II on (rmse, n_params)
    over a closed capacity×lr×activation catalog (native multi-obj path).
    """
    if seeds is not None and len(seeds) > 1:
        return _hybrid_multiseed(
            x,
            y,
            seeds=list(seeds),
            max_evaluations=max_evaluations,
            max_generations=max_generations,
            population_size=population_size,
            max_wall_time_s=max_wall_time_s,
            inner_epochs=inner_epochs,
            early_stopping_patience=early_stopping_patience,
            device=device,
            val_fraction=val_fraction,
            facets=facets,
        )
    if multiobjective:
        return multiobjective_neural_search(
            x,
            y,
            seed=seed,
            max_generations=max_generations or max(4, max_evaluations // max(population_size, 4)),
            population_size=population_size,
            inner_epochs=inner_epochs,
            device=device,
            val_fraction=val_fraction,
        )

    ng = _require_nevergrad()
    facets = facets or ["hyperparameters", "architecture"]
    t0 = time.perf_counter()
    budget = int(max_evaluations)
    if max_generations is not None:
        budget = min(budget, max(4, max_generations * max(population_size, 1)))

    capacity_choices = ("tiny", "medium", "dense")
    lr_choices = (1e-3, 3e-3, 1e-2, 3e-2)
    act_choices = (ActivationName.RELU, ActivationName.GELU, ActivationName.TANH)
    opt_choices = (OptimizerName.ADAM, OptimizerName.ADAMW, OptimizerName.SGD)
    policy_choices = ("short", "standard", "long")  # maps to epochs multiplier
    n_feat = len(x[0]) if x else 1

    params: dict[str, Any] = {
        "cap": ng.p.Choice(list(range(len(capacity_choices)))),
        "lr": ng.p.Choice(list(range(len(lr_choices)))),
        "act": ng.p.Choice(list(range(len(act_choices)))),
        "opt": ng.p.Choice(list(range(len(opt_choices)))),
        "wd": ng.p.Choice([0.0, 1e-4, 1e-3]),
        "dropout": ng.p.Choice([0.0, 0.1, 0.2]),
        "batch": ng.p.Choice([8, 16, 32]),
    }
    if "features" in facets and n_feat > 1:
        # up to min(8, n_feat) binary flags (closed, not free mask length)
        k = min(8, n_feat)
        for i in range(k):
            params[f"f{i}"] = ng.p.Choice([0, 1])
        params["n_feature_flags"] = ng.p.Choice([k])  # constant-ish
    if "loss_weights" in facets:
        params["lam_mse"] = ng.p.Choice([0.5, 1.0, 1.5])
        params["lam_mae"] = ng.p.Choice([0.0, 0.25, 0.5])
        params["lam_size"] = ng.p.Choice([0.0, 0.1, 0.5])
    if "policy" in facets:
        params["policy"] = ng.p.Choice(list(range(len(policy_choices))))

    instrum = ng.p.Dict(**params)
    opt = ng.optimizers.OnePlusOne(parametrization=instrum, budget=budget)
    with __import__("contextlib").suppress(Exception):
        opt.parametrization.random_state.seed(seed)

    trials: list[dict[str, Any]] = []

    def _score(p: dict[str, Any]) -> float:
        if max_wall_time_s is not None and (time.perf_counter() - t0) >= max_wall_time_s:
            return 1e6
        cap = capacity_choices[int(p["cap"])]
        knobs = resolve_capacity("mlp", cap)  # type: ignore[arg-type]
        hidden = list(knobs["hidden_dims"])
        lr = float(lr_choices[int(p["lr"])])
        act = act_choices[int(p["act"])]
        optn = opt_choices[int(p["opt"])]
        epochs = inner_epochs
        if "policy" in p:
            pol = policy_choices[int(p["policy"])]
            epochs = {
                "short": max(5, inner_epochs // 2),
                "standard": inner_epochs,
                "long": inner_epochs * 2,
            }[pol]
        mask = None
        if "features" in facets and n_feat > 1:
            k = min(8, n_feat)
            flags = [bool(int(p.get(f"f{i}", 1))) for i in range(k)]
            # pad remaining features as always-on
            mask = flags + [True] * (n_feat - k)
            if not any(mask):
                mask[0] = True
        lw = {"mse": 1.0}
        if "loss_weights" in facets:
            lw = {
                "mse": float(p.get("lam_mse", 1.0)),
                "mae": float(p.get("lam_mae", 0.0)),
                "size": float(p.get("lam_size", 0.0)),
            }
        out = _train_candidate(
            x,
            y,
            hidden_dims=hidden,
            activation=act,
            lr=lr,
            weight_decay=float(p.get("wd", 0.0)),
            dropout=float(p.get("dropout", 0.0)),
            optimizer=optn,
            momentum=0.9 if optn == OptimizerName.SGD else 0.0,
            epochs=int(epochs),
            batch_size=int(p.get("batch", 16)),
            seed=seed,
            device=device,
            val_fraction=val_fraction,
            loss_weights=lw,
            early_stopping_patience=early_stopping_patience,
            feature_mask=mask,
        )
        out["capacity"] = cap
        if "policy" in p:
            out["policy"] = policy_choices[int(p["policy"])]
        trials.append(out)
        return float(out["score"])

    recommendation = opt.minimize(_score)
    best = min(trials, key=lambda t: t["score"]) if trials else None
    # Pareto (loss, n_params) among trials
    pareto = _pareto_front(trials)

    return {
        "mode": "hybrid",
        "pipeline": "evolutionary_search→gradient_train→evaluate→evolution",
        "seed": seed,
        "budget": {
            "max_evaluations": budget,
            "population_size": population_size,
            "max_generations": max_generations,
            "max_wall_time_s": max_wall_time_s,
        },
        "inner_training": {
            "max_epochs": inner_epochs,
            "early_stopping_patience": early_stopping_patience,
            "device": device,
        },
        "facets": facets,
        "best_config": best,
        "n_trials": len(trials),
        "trials": trials[-min(15, len(trials)) :],
        "pareto_front": pareto,
        "elapsed_seconds": time.perf_counter() - t0,
        "backends": {"outer": "nevergrad", "inner": "torch"},
        "problem_fingerprint": problem_fingerprint(
            {"n": len(x), "d": n_feat, "budget": budget, "seed": seed, "facets": facets}
        ),
        "recommendation_raw": dict(recommendation.value) if recommendation is not None else {},
        "message": "ok",
        "policy": (
            "Hybrid evolutionary neural training (ADR 0033): outer Nevergrad explores "
            "closed config space; PyTorch optimizes weights per candidate. "
            "Re-train final model with best_config for production."
        ),
    }


def _pareto_front(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Non-dominated set on (rmse, n_params) minimization."""
    pts = [
        t
        for t in trials
        if t.get("rmse") is not None and t.get("n_params") is not None and "error" not in t
    ]
    front: list[dict[str, Any]] = []
    for i, a in enumerate(pts):
        dominated = False
        for j, b in enumerate(pts):
            if i == j:
                continue
            if (
                float(b["rmse"]) <= float(a["rmse"])
                and int(b["n_params"]) <= int(a["n_params"])
                and (float(b["rmse"]) < float(a["rmse"]) or int(b["n_params"]) < int(a["n_params"]))
            ):
                dominated = True
                break
        if not dominated:
            front.append(
                {
                    "rmse": a["rmse"],
                    "n_params": a["n_params"],
                    "r_squared": a.get("r_squared"),
                    "hidden_dims": a.get("hidden_dims"),
                    "capacity": a.get("capacity"),
                }
            )
    return front


def neuroevolution_train(
    x: list[list[float]],
    y: list[float],
    *,
    max_evaluations: int = 40,
    seed: int = 42,
    hidden: int = 8,
    max_params: int = 500,
    device: str = "cpu",
) -> dict[str, Any]:
    """Direct neuroevolution of small MLP weights (Nevergrad black-box, ADR 0033 W4).

    Hard-capped by ``max_params`` — not for large nets (use hybrid instead).
    """
    ng = _require_nevergrad()
    try:
        import torch
    except ImportError as exc:
        raise TorchNotAvailableError(
            "PyTorch is not installed. Install with: uv sync --extra neural"
        ) from exc

    d = len(x[0])
    # Single hidden layer small MLP: d -> H -> 1
    n_params = d * hidden + hidden + hidden * 1 + 1
    if n_params > max_params:
        raise ValueError(
            f"neuroevolution model has {n_params} params > max_params={max_params}; "
            "use hybrid training for larger models (ADR 0033)"
        )

    x_t = torch.tensor(x, dtype=torch.float32)
    y_t = torch.tensor(y, dtype=torch.float32).view(-1, 1)
    # normalize
    mean = x_t.mean(0, keepdim=True)
    std = x_t.std(0, keepdim=True).clamp(min=1e-6)
    x_n = (x_t - mean) / std

    def _forward(w: np.ndarray) -> float:
        # unpack weights
        w = np.asarray(w, dtype=np.float64).reshape(-1)
        i = 0
        w1 = torch.tensor(w[i : i + d * hidden].reshape(d, hidden), dtype=torch.float32)
        i += d * hidden
        b1 = torch.tensor(w[i : i + hidden], dtype=torch.float32)
        i += hidden
        w2 = torch.tensor(w[i : i + hidden].reshape(hidden, 1), dtype=torch.float32)
        i += hidden
        b2 = torch.tensor(w[i : i + 1], dtype=torch.float32)
        h = torch.tanh(x_n @ w1 + b1)
        pred = h @ w2 + b2
        return float(torch.mean((pred - y_t) ** 2).item())

    instrum = ng.p.Array(shape=(n_params,)).set_bounds(-2.0, 2.0)
    opt = ng.optimizers.OnePlusOne(parametrization=instrum, budget=max_evaluations)
    with __import__("contextlib").suppress(Exception):
        opt.parametrization.random_state.seed(seed)
    recommendation = opt.minimize(_forward)
    best_w = np.asarray(recommendation.value, dtype=float).reshape(-1)
    best_mse = _forward(best_w)

    return {
        "mode": "neuroevolution",
        "pipeline": "evolutionary_weight_search",
        "seed": seed,
        "budget": {"max_evaluations": max_evaluations, "max_params": max_params},
        "architecture": {"input_dim": d, "hidden": hidden, "output_dim": 1},
        "n_params": n_params,
        "best_mse": best_mse,
        "backends": {"outer": "nevergrad", "inner": "torch_forward_only"},
        "problem_fingerprint": problem_fingerprint(
            {"n": len(x), "d": d, "hidden": hidden, "budget": max_evaluations, "seed": seed}
        ),
        "message": "ok",
        "policy": (
            "Direct weight neuroevolution for small models only. "
            "Prefer hybrid evolutionary→gradient for larger nets (ADR 0033)."
        ),
    }


def benchmark_training_strategies(
    x: list[list[float]],
    y: list[float],
    *,
    seed: int = 42,
    max_evaluations: int = 12,
    inner_epochs: int = 15,
    device: str = "cpu",
) -> dict[str, Any]:
    """Compare gradient-only vs hybrid under shared outer budget (ADR 0033 §11)."""
    t0 = time.perf_counter()
    # Arm A: gradient only with default medium capacity
    knobs = resolve_capacity("mlp", "medium")
    grad = _train_candidate(
        x,
        y,
        hidden_dims=list(knobs["hidden_dims"]),
        activation=ActivationName.RELU,
        lr=1e-2,
        weight_decay=0.0,
        dropout=0.0,
        optimizer=OptimizerName.ADAMW,
        momentum=0.0,
        epochs=inner_epochs,
        batch_size=16,
        seed=seed,
        device=device,
        val_fraction=0.25,
    )
    grad_arm = {
        "strategy": "gradient_only",
        "rmse": grad.get("rmse"),
        "r_squared": grad.get("r_squared"),
        "n_params": grad.get("n_params"),
        "n_evaluations": 1,
        "score": grad.get("score"),
    }

    # Arm B: hybrid
    hybrid = hybrid_evolutionary_train(
        x,
        y,
        max_evaluations=max_evaluations,
        seed=seed,
        inner_epochs=inner_epochs,
        device=device,
        facets=["hyperparameters", "architecture"],
    )
    best = hybrid.get("best_config") or {}
    hybrid_arm = {
        "strategy": "hybrid_evolutionary_gradient",
        "rmse": best.get("rmse"),
        "r_squared": best.get("r_squared"),
        "n_params": best.get("n_params"),
        "n_evaluations": hybrid.get("n_trials"),
        "score": best.get("score"),
    }

    # Arm C: neuroevolution (small) if feasible
    neuro_arm: dict[str, Any]
    try:
        neuro = neuroevolution_train(
            x, y, max_evaluations=max_evaluations, seed=seed, hidden=4, max_params=500
        )
        neuro_arm = {
            "strategy": "neuroevolution_weights",
            "best_mse": neuro.get("best_mse"),
            "n_params": neuro.get("n_params"),
            "n_evaluations": max_evaluations,
            "score": neuro.get("best_mse"),
        }
    except Exception as exc:  # noqa: BLE001
        neuro_arm = {"strategy": "neuroevolution_weights", "error": str(exc), "skipped": True}

    return {
        "mode": "benchmark_training_strategy",
        "seed": seed,
        "shared_budget": {
            "max_evaluations": max_evaluations,
            "inner_epochs": inner_epochs,
        },
        "arms": [grad_arm, hybrid_arm, neuro_arm],
        "elapsed_seconds": time.perf_counter() - t0,
        "message": "ok",
        "policy": (
            "No strategy is declared superior a priori (ADR 0033). "
            "Compare arms under the shared budget only."
        ),
        "problem_fingerprint": problem_fingerprint(
            {"n": len(x), "budget": max_evaluations, "seed": seed}
        ),
    }


# Aliases for search facets
def search_hyperparameters(x: list[list[float]], y: list[float], **kwargs: Any) -> dict[str, Any]:
    return hybrid_evolutionary_train(x, y, facets=["hyperparameters", "architecture"], **kwargs)


def search_architecture(x: list[list[float]], y: list[float], **kwargs: Any) -> dict[str, Any]:
    return hybrid_evolutionary_train(x, y, facets=["architecture"], multiobjective=True, **kwargs)


def search_features(x: list[list[float]], y: list[float], **kwargs: Any) -> dict[str, Any]:
    return hybrid_evolutionary_train(x, y, facets=["features", "hyperparameters"], **kwargs)


def search_loss_weights(x: list[list[float]], y: list[float], **kwargs: Any) -> dict[str, Any]:
    return hybrid_evolutionary_train(x, y, facets=["loss_weights", "hyperparameters"], **kwargs)


def search_policy(x: list[list[float]], y: list[float], **kwargs: Any) -> dict[str, Any]:
    return hybrid_evolutionary_train(
        x, y, facets=["policy", "hyperparameters", "architecture"], **kwargs
    )


def _hybrid_multiseed(
    x: list[list[float]],
    y: list[float],
    *,
    seeds: list[int],
    max_evaluations: int,
    max_generations: int | None,
    population_size: int,
    max_wall_time_s: float | None,
    inner_epochs: int,
    early_stopping_patience: int,
    device: str,
    val_fraction: float,
    facets: list[str] | None,
) -> dict[str, Any]:
    """Run hybrid once per outer seed; report mean±std of best scores."""
    rows: list[dict[str, Any]] = []
    scores: list[float] = []
    for s in seeds:
        rep = hybrid_evolutionary_train(
            x,
            y,
            max_evaluations=max_evaluations,
            max_generations=max_generations,
            population_size=population_size,
            max_wall_time_s=max_wall_time_s,
            seed=s,
            seeds=None,
            inner_epochs=inner_epochs,
            early_stopping_patience=early_stopping_patience,
            device=device,
            val_fraction=val_fraction,
            facets=facets,
            multiobjective=False,
        )
        best = rep.get("best_config") or {}
        sc = float(best.get("score", 1e6))
        scores.append(sc)
        rows.append(
            {
                "seed": s,
                "best_score": sc,
                "best_rmse": best.get("rmse"),
                "best_n_params": best.get("n_params"),
                "n_trials": rep.get("n_trials"),
                "best_config": best,
            }
        )
    arr = np.asarray(scores, dtype=float)
    return {
        "mode": "hybrid_multiseed",
        "pipeline": "multi_seed_outer→hybrid_evolutionary_gradient",
        "seeds": list(seeds),
        "facets": facets or ["hyperparameters", "architecture"],
        "rows": rows,
        "mean_best_score": float(np.mean(arr)),
        "std_best_score": float(np.std(arr)),
        "min_best_score": float(np.min(arr)),
        "max_best_score": float(np.max(arr)),
        "best_config": min(rows, key=lambda r: r["best_score"])["best_config"],
        "budget": {
            "max_evaluations_per_seed": max_evaluations,
            "n_seeds": len(seeds),
            "total_evaluations_cap": max_evaluations * len(seeds),
            "max_generations": max_generations,
            "population_size": population_size,
            "max_wall_time_s": max_wall_time_s,
        },
        "inner_training": {
            "max_epochs": inner_epochs,
            "early_stopping_patience": early_stopping_patience,
            "device": device,
            "val_fraction": val_fraction,
        },
        "backends": {"outer": "nevergrad", "inner": "torch", "aggregation": "multi_seed"},
        "message": "ok",
        "policy": (
            "Outer multi-seed hybrid: each seed runs a full evo→gradient search. "
            "Report mean±std of best scores; no strategy declared superior a priori."
        ),
        "problem_fingerprint": problem_fingerprint(
            {"n": len(x), "seeds": seeds, "budget": max_evaluations}
        ),
    }


def multiobjective_neural_search(
    x: list[list[float]],
    y: list[float],
    *,
    seed: int = 42,
    max_generations: int = 6,
    population_size: int = 8,
    inner_epochs: int = 12,
    device: str = "cpu",
    val_fraction: float = 0.25,
) -> dict[str, Any]:
    """Native pymoo NSGA-II multi-obj search over closed neural catalog.

    Decision vars (int indices): capacity, learning_rate, activation.
    Objectives (minimize): validation RMSE, parameter count.
    """
    try:
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.problem import Problem
        from pymoo.operators.crossover.sbx import SBX
        from pymoo.operators.mutation.pm import PM
        from pymoo.operators.repair.rounding import RoundingRepair
        from pymoo.operators.sampling.rnd import IntegerRandomSampling
        from pymoo.optimize import minimize
    except ImportError as exc:
        raise PymooNotAvailableError(
            "pymoo is not installed. Install with: uv sync --extra evolutionary"
        ) from exc

    capacity_choices = ("tiny", "medium", "dense")
    lr_choices = (1e-3, 3e-3, 1e-2, 3e-2)
    act_choices = (ActivationName.RELU, ActivationName.GELU, ActivationName.TANH)
    trials: list[dict[str, Any]] = []

    class _NeuralCatalogProblem(Problem):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__(
                n_var=3,
                n_obj=2,
                n_ieq_constr=0,
                xl=np.array([0, 0, 0]),
                xu=np.array(
                    [
                        len(capacity_choices) - 1,
                        len(lr_choices) - 1,
                        len(act_choices) - 1,
                    ]
                ),
                vtype=int,
            )

        def _evaluate(
            self, x_mat: np.ndarray, out: dict[str, Any], *args: Any, **kwargs: Any
        ) -> None:
            f = np.empty((x_mat.shape[0], 2), dtype=float)
            for i in range(x_mat.shape[0]):
                ci = int(np.clip(round(float(x_mat[i, 0])), 0, len(capacity_choices) - 1))
                li = int(np.clip(round(float(x_mat[i, 1])), 0, len(lr_choices) - 1))
                ai = int(np.clip(round(float(x_mat[i, 2])), 0, len(act_choices) - 1))
                cap = capacity_choices[ci]
                knobs = resolve_capacity("mlp", cap)  # type: ignore[arg-type]
                cand = _train_candidate(
                    x,
                    y,
                    hidden_dims=list(knobs["hidden_dims"]),
                    activation=act_choices[ai],
                    lr=float(lr_choices[li]),
                    weight_decay=0.0,
                    dropout=0.0,
                    optimizer=OptimizerName.ADAMW,
                    momentum=0.0,
                    epochs=inner_epochs,
                    batch_size=16,
                    seed=seed,
                    device=device,
                    val_fraction=val_fraction,
                )
                rmse = float(cand.get("rmse", 1e3))
                n_params = float(cand.get("n_params") or 1e6)
                f[i, 0] = rmse
                f[i, 1] = n_params
                cand["capacity"] = cap
                cand["lr"] = float(lr_choices[li])
                cand["activation"] = act_choices[ai].value
                trials.append(cand)
            out["F"] = f

    algo = NSGA2(
        pop_size=population_size,
        sampling=IntegerRandomSampling(),
        crossover=SBX(prob=0.9, eta=15, vtype=float, repair=RoundingRepair()),
        mutation=PM(eta=20, vtype=float, repair=RoundingRepair()),
        eliminate_duplicates=True,
    )
    res = minimize(
        _NeuralCatalogProblem(),
        algo,
        termination=("n_gen", max_generations),
        seed=seed,
        verbose=False,
    )
    pareto: list[dict[str, Any]] = []
    if res.F is not None:
        f_mat = np.atleast_2d(np.asarray(res.F, dtype=float))
        x_mat = np.atleast_2d(np.asarray(res.X, dtype=float)) if res.X is not None else None
        for i in range(f_mat.shape[0]):
            entry: dict[str, Any] = {
                "rmse": float(f_mat[i, 0]),
                "n_params": int(f_mat[i, 1]),
            }
            if x_mat is not None:
                ci = int(np.clip(round(float(x_mat[i, 0])), 0, len(capacity_choices) - 1))
                li = int(np.clip(round(float(x_mat[i, 1])), 0, len(lr_choices) - 1))
                ai = int(np.clip(round(float(x_mat[i, 2])), 0, len(act_choices) - 1))
                entry["capacity"] = capacity_choices[ci]
                entry["lr"] = float(lr_choices[li])
                entry["activation"] = act_choices[ai].value
            pareto.append(entry)
    if not pareto:
        pareto = _pareto_front(trials)

    best = min(pareto, key=lambda p: (p["rmse"], p["n_params"])) if pareto else None
    return {
        "mode": "multiobjective_neural_search",
        "pipeline": "pymoo_nsga2→gradient_train→pareto(rmse,n_params)",
        "seed": seed,
        "budget": {
            "max_generations": max_generations,
            "population_size": population_size,
            "inner_epochs": inner_epochs,
            "max_evaluations_est": max_generations * population_size,
        },
        "objectives": ["rmse", "n_params"],
        "pareto_front": pareto,
        "best_compromise": best,
        "best_config": best,
        "n_trials": len(trials),
        "trials": trials[-min(20, len(trials)) :],
        "backends": {"outer": "pymoo", "inner": "torch", "algorithm": "nsga2"},
        "message": "ok",
        "policy": (
            "Multi-objective neural search (ADR 0033 industrial). "
            "Pareto over validation RMSE and parameter count."
        ),
        "problem_fingerprint": problem_fingerprint(
            {
                "n": len(x),
                "seed": seed,
                "gens": max_generations,
                "pop": population_size,
                "mode": "nsga2_neural",
            }
        ),
    }
