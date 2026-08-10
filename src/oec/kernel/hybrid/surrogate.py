"""Neural surrogate + evolutionary search + high-fidelity verify (X2)."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.evolutionary.contracts import BuiltInProblemName
from oec.evolutionary.hashing import problem_fingerprint
from oec.kernel.evolutionary.errors import NevergradNotAvailableError
from oec.kernel.evolutionary.problems import evaluate_built_in
from oec.kernel.neural.errors import TorchNotAvailableError
from oec.kernel.neural.training import predict_mlp, train_mlp
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


def _sample_expensive(
    built_in: BuiltInProblemName,
    n_var: int,
    n_samples: int,
    lower: float,
    upper: float,
    seed: int,
) -> tuple[list[list[float]], list[float]]:
    """Sample the true (high-fidelity) objective — stand-in for expensive simulator."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(lower, upper, size=(n_samples, n_var))
    y = [evaluate_built_in(built_in, row) for row in x]
    return x.tolist(), y


def surrogate_then_evolve(
    *,
    built_in: str = "sphere",
    n_var: int = 2,
    lower: float = -5.0,
    upper: float = 5.0,
    n_train: int = 80,
    surrogate_epochs: int = 60,
    evo_budget: int = 120,
    optimizer: str = "OnePlusOne",
    seed: int = 42,
    n_verify: int = 5,
    device: str = "cpu",
) -> dict[str, Any]:
    """Train MLP on samples of true f, optimize surrogate, verify on true f.

    Pipeline:
      sample true f → train neural surrogate → nevergrad on surrogate
      → re-evaluate top candidates on true f (high-fidelity gate)
    """
    problem = BuiltInProblemName(built_in)
    x_list, y_list = _sample_expensive(problem, n_var, n_train, lower, upper, seed)

    # Train surrogate (minimize prediction of f)
    try:
        train_result = train_mlp(
            DatasetSpec(x=x_list, y=y_list, val_fraction=0.2),
            NeuralModelSpec(
                architecture="mlp",
                input_dim=n_var,
                output_dim=1,
                hidden_dims=[32, 16],
                activation=ActivationName.RELU,
            ),
            TrainingSpec(
                task=NeuralTask.REGRESSION,
                epochs=surrogate_epochs,
                batch_size=min(16, max(4, n_train // 4)),
                loss=LossName.MSE,
                optimizer=OptimizerSpec(name=OptimizerName.ADAM, lr=1e-2),
                seed=seed,
                device=DeviceSpec(device=device if device in ("cpu", "cuda", "auto") else "cpu"),
                normalize_x=True,
                early_stopping_patience=15,
            ),
        )
    except TorchNotAvailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"surrogate training failed: {exc}") from exc

    dumped = train_result.model_dump(mode="json")
    ckpt = dumped["checkpoint"]
    norm = dumped.get("normalize")

    def surrogate_fn(x: np.ndarray) -> float:
        pred = predict_mlp(
            [list(map(float, x.reshape(-1)))],
            ckpt,
            normalize=norm,
            device=device,
        )
        first = pred[0]
        if isinstance(first, list):
            return float(first[0])
        return float(first)

    # Evolve on surrogate (cheap)
    try:
        from oec.kernel.evolutionary.blackbox import ALLOWED_OPTIMIZERS, _require_nevergrad

        ng = _require_nevergrad()
        if optimizer not in ALLOWED_OPTIMIZERS:
            raise ValueError(f"optimizer {optimizer!r} not allowed")
        instrum = ng.p.Array(shape=(n_var,)).set_bounds(lower, upper)
        opt = ng.optimizers.registry[optimizer](
            parametrization=instrum, budget=evo_budget, num_workers=1
        )
        with __import__("contextlib").suppress(Exception):
            opt.parametrization.random_state.seed(seed + 1)

        rec = opt.minimize(lambda x: surrogate_fn(np.asarray(x, dtype=float)))
        x_surr = np.asarray(rec.value, dtype=float).reshape(-1)
    except NevergradNotAvailableError:
        raise
    except Exception:  # noqa: BLE001
        # fallback: random search on surrogate
        rng = np.random.default_rng(seed + 1)
        best_x = None
        best_s = float("inf")
        for _ in range(evo_budget):
            cand = rng.uniform(lower, upper, size=n_var)
            s = surrogate_fn(cand)
            if s < best_s:
                best_s = s
                best_x = cand
        x_surr = best_x if best_x is not None else np.zeros(n_var)

    f_surr = float(surrogate_fn(x_surr))
    f_true = float(evaluate_built_in(problem, x_surr))

    # High-fidelity verify: local re-sample around candidate + true evaluate
    rng = np.random.default_rng(seed + 2)
    verified: list[dict[str, Any]] = [
        {
            "x": {f"x{i}": float(x_surr[i]) for i in range(n_var)},
            "surrogate_f": f_surr,
            "true_f": f_true,
            "source": "evo_on_surrogate",
        }
    ]
    for _ in range(max(0, n_verify - 1)):
        cand = x_surr + rng.normal(0, 0.1 * (upper - lower), size=n_var)
        cand = np.clip(cand, lower, upper)
        verified.append(
            {
                "x": {f"x{i}": float(cand[i]) for i in range(n_var)},
                "surrogate_f": float(surrogate_fn(cand)),
                "true_f": float(evaluate_built_in(problem, cand)),
                "source": "local_true_recheck",
            }
        )
    best_true = min(verified, key=lambda r: float(r["true_f"]))

    # Policy: surrogate_accepted is ALWAYS false as engineering truth
    return {
        "pipeline": "sample→surrogate_mlp→evo→high_fidelity_verify",
        "built_in": built_in,
        "seed": seed,
        "n_var": n_var,
        "surrogate": {
            "backend": "torch",
            "train_metrics": train_result.train_metrics,
            "val_metrics": train_result.val_metrics,
            "epochs_ran": train_result.epochs_ran,
            "dataset_fingerprint": train_result.dataset_fingerprint,
        },
        "evo_on_surrogate": {
            "optimizer": optimizer,
            "budget": evo_budget,
            "x": {f"x{i}": float(x_surr[i]) for i in range(n_var)},
            "surrogate_objective": f_surr,
            "true_objective_at_surrogate_x": f_true,
        },
        "high_fidelity": {
            "candidates": verified,
            "best_true": best_true,
            "accepted_as_engineering_truth": False,
            "policy": (
                "Surrogate optimum is a proposal only. "
                "Use high_fidelity.best_true for engineering decisions; "
                "never promote surrogate_f alone (X2)."
            ),
        },
        "problem_fingerprint": problem_fingerprint(
            {
                "built_in": built_in,
                "n_var": n_var,
                "n_train": n_train,
                "evo_budget": evo_budget,
                "seed": seed,
            }
        ),
        "message": "ok",
    }
