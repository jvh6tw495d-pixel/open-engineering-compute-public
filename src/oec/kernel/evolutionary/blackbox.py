"""Black-box optimization via Nevergrad (E4)."""

from __future__ import annotations

import contextlib
from typing import Any

import numpy as np

from oec.evolutionary.contracts import BuiltInProblemName
from oec.evolutionary.hashing import problem_fingerprint
from oec.kernel.evolutionary.errors import NevergradNotAvailableError
from oec.kernel.evolutionary.problems import evaluate_built_in

# Closed optimizer allow-list (nevergrad class names / registry keys)
ALLOWED_OPTIMIZERS: frozenset[str] = frozenset(
    {
        "NGOpt",
        "TwoPointsDE",
        "OnePlusOne",
        "CMA",
        "PSO",
        "RandomSearch",
        "TBPSA",
        "MetaTuneRecentering",
    }
)


def _require_nevergrad() -> Any:
    try:
        import nevergrad as ng
    except ImportError as exc:
        raise NevergradNotAvailableError(
            "nevergrad is not installed. Install with: uv sync --extra evolutionary"
        ) from exc
    return ng


def _ng_version() -> str | None:
    try:
        import importlib.metadata

        return importlib.metadata.version("nevergrad")
    except Exception:  # noqa: BLE001
        return None


def blackbox_optimize(
    *,
    built_in: str = "sphere",
    n_var: int = 2,
    lower: float = -5.0,
    upper: float = 5.0,
    budget: int = 200,
    optimizer: str = "NGOpt",
    seed: int = 42,
) -> dict[str, Any]:
    """Optimize a built-in SOO problem with a Nevergrad optimizer."""
    ng = _require_nevergrad()
    if optimizer not in ALLOWED_OPTIMIZERS:
        raise ValueError(
            f"optimizer {optimizer!r} not allowed; choose from {sorted(ALLOWED_OPTIMIZERS)}"
        )
    problem = BuiltInProblemName(built_in)
    instrum = ng.p.Array(shape=(n_var,)).set_bounds(lower, upper)
    opt_cls = ng.optimizers.registry[optimizer]
    opt = opt_cls(parametrization=instrum, budget=budget, num_workers=1)
    # seed if supported
    with contextlib.suppress(Exception):
        opt.parametrization.random_state.seed(seed)

    def _fn(x: np.ndarray) -> float:
        return evaluate_built_in(problem, np.asarray(x, dtype=float))

    recommendation = opt.minimize(_fn)
    x_best = np.asarray(recommendation.value, dtype=float).reshape(-1)
    f_best = float(_fn(x_best))

    return {
        "backend": "nevergrad",
        "backend_version": _ng_version(),
        "algorithm": optimizer,
        "seed": seed,
        "deterministic_status": "practical",
        "built_in": built_in,
        "best_objective": f_best,
        "best_x": {f"x{i}": float(x_best[i]) for i in range(n_var)},
        "budget": budget,
        "n_evaluations": int(getattr(opt, "num_ask", budget)),
        "problem_fingerprint": problem_fingerprint(
            {
                "built_in": built_in,
                "n_var": n_var,
                "lower": lower,
                "upper": upper,
                "budget": budget,
                "optimizer": optimizer,
                "seed": seed,
            }
        ),
        "message": "ok",
    }


def optimizer_portfolio(
    *,
    built_in: str = "sphere",
    n_var: int = 2,
    lower: float = -5.0,
    upper: float = 5.0,
    budget: int = 150,
    optimizers: list[str] | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Run several Nevergrad optimizers under the same budget; report table."""
    opts = optimizers or ["OnePlusOne", "TwoPointsDE", "CMA", "RandomSearch"]
    for name in opts:
        if name not in ALLOWED_OPTIMIZERS:
            raise ValueError(f"optimizer {name!r} not allowed")

    rows: list[dict[str, Any]] = []
    for i, name in enumerate(opts):
        res = blackbox_optimize(
            built_in=built_in,
            n_var=n_var,
            lower=lower,
            upper=upper,
            budget=budget,
            optimizer=name,
            seed=seed + i,
        )
        rows.append(
            {
                "optimizer": name,
                "best_objective": res["best_objective"],
                "best_x": res["best_x"],
                "budget": budget,
                "seed": seed + i,
            }
        )
    best_row = min(rows, key=lambda r: float(r["best_objective"]))
    return {
        "backend": "nevergrad",
        "backend_version": _ng_version(),
        "algorithm": "optimizer_portfolio",
        "seed": seed,
        "deterministic_status": "practical",
        "built_in": built_in,
        "budget": budget,
        "optimizers": opts,
        "rows": rows,
        "best_optimizer": best_row["optimizer"],
        "best_objective": best_row["best_objective"],
        "best_x": best_row["best_x"],
        "problem_fingerprint": problem_fingerprint(
            {
                "built_in": built_in,
                "n_var": n_var,
                "budget": budget,
                "optimizers": opts,
                "seed": seed,
            }
        ),
        "message": (
            "best_optimizer is lowest best_objective under shared budget; "
            "not a universal claim of superiority (X1 principle)."
        ),
    }
