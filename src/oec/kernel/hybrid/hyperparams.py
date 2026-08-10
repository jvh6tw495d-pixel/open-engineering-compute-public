"""Evolutionary search over neural hyperparameters (X2)."""

from __future__ import annotations

from typing import Any

from oec.evolutionary.hashing import problem_fingerprint
from oec.kernel.evolutionary.errors import NevergradNotAvailableError
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


def evo_hyperparameter_search(
    x: list[list[float]],
    y: list[float],
    *,
    budget: int = 12,
    seed: int = 42,
    epochs: int = 25,
    device: str = "cpu",
    task: str = "regression",
) -> dict[str, Any]:
    """Search MLP hyperparams with Nevergrad; score = val loss / (1+R²).

    Discrete choices from closed enums only (no arbitrary architectures).
    """
    try:
        import nevergrad as ng
    except ImportError as exc:
        raise NevergradNotAvailableError(
            "nevergrad is not installed. Install with: uv sync --extra evolutionary"
        ) from exc

    # Search space: indices into closed catalogs
    hidden_choices = ([16], [32], [32, 16], [64, 32], [64, 32, 16])
    lr_choices = (1e-3, 3e-3, 1e-2, 3e-2)
    act_choices = (ActivationName.RELU, ActivationName.GELU, ActivationName.TANH)

    instrum = ng.p.Dict(
        h=ng.p.Choice(list(range(len(hidden_choices)))),
        lr=ng.p.Choice(list(range(len(lr_choices)))),
        act=ng.p.Choice(list(range(len(act_choices)))),
    )
    opt = ng.optimizers.OnePlusOne(parametrization=instrum, budget=budget)
    with __import__("contextlib").suppress(Exception):
        opt.parametrization.random_state.seed(seed)

    trials: list[dict[str, Any]] = []

    def _score(params: dict[str, Any]) -> float:
        h_idx = int(params["h"])
        lr_idx = int(params["lr"])
        act_idx = int(params["act"])
        hidden = list(hidden_choices[h_idx])
        lr = float(lr_choices[lr_idx])
        act = act_choices[act_idx]
        try:
            result = train_mlp(
                DatasetSpec(x=x, y=y, val_fraction=0.25),
                NeuralModelSpec(
                    architecture="mlp",
                    input_dim=len(x[0]),
                    output_dim=1,
                    hidden_dims=hidden,
                    activation=act,
                ),
                TrainingSpec(
                    task=NeuralTask.REGRESSION
                    if task == "regression"
                    else NeuralTask.BINARY_CLASSIFICATION,
                    epochs=epochs,
                    batch_size=min(16, max(4, len(x) // 4)),
                    loss=LossName.MSE,
                    optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=lr),
                    seed=seed,
                    device=DeviceSpec(
                        device=device if device in ("cpu", "cuda", "auto") else "cpu"
                    ),
                    normalize_x=True,
                    early_stopping_patience=8,
                ),
            )
        except TorchNotAvailableError:
            raise
        except Exception:  # noqa: BLE001
            return 1e6

        metrics = result.val_metrics or result.train_metrics
        # minimize: prefer low rmse / high r2
        rmse = float(metrics.get("rmse", 1e3))
        r2 = float(metrics.get("r_squared", -1.0))
        score = rmse / max(1e-6, 1.0 + max(r2, -0.99))
        trials.append(
            {
                "hidden_dims": hidden,
                "lr": lr,
                "activation": act.value,
                "rmse": rmse,
                "r_squared": r2,
                "score": score,
            }
        )
        return score

    recommendation = opt.minimize(_score)
    best_params = recommendation.value
    h_idx = int(best_params["h"])
    lr_idx = int(best_params["lr"])
    act_idx = int(best_params["act"])
    best_cfg = {
        "hidden_dims": list(hidden_choices[h_idx]),
        "lr": float(lr_choices[lr_idx]),
        "activation": act_choices[act_idx].value,
    }
    best_trial = min(trials, key=lambda t: t["score"]) if trials else None

    return {
        "pipeline": "evo_hyperparameter_search→mlp",
        "seed": seed,
        "budget": budget,
        "epochs_per_trial": epochs,
        "best_config": best_cfg,
        "best_trial_metrics": best_trial,
        "n_trials": len(trials),
        "trials": trials[-min(10, len(trials)) :],
        "problem_fingerprint": problem_fingerprint(
            {"n": len(x), "d": len(x[0]) if x else 0, "budget": budget, "seed": seed}
        ),
        "message": "ok",
        "policy": (
            "Hyperparameters are selected by validation score on provided data only; "
            "re-train final model with best_config for production use."
        ),
    }
