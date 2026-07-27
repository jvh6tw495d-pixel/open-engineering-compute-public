"""Morris elementary-effects screening (light). Merit: NumPy.

Evaluates a declared multilinear model ``f(x) = c0 + c·x`` so the skill stays
free of arbitrary code execution (ADR 0012 sandbox safety).
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _eval_linear(x: np.ndarray, intercept: float, coeffs: np.ndarray) -> float:
    return float(intercept + float(np.dot(coeffs, x)))


def morris_screen(
    bounds: list[list[float]],
    coeffs: list[float],
    *,
    intercept: float = 0.0,
    n_trajectories: int = 10,
    n_levels: int = 4,
    seed: int | None = None,
) -> dict[str, Any]:
    """Morris elementary effects for a linear model on a hyper-rectangle.

    Parameters
    ----------
    bounds:
        ``[low, high]`` per factor.
    coeffs:
        Linear coefficients (same length as ``bounds``).
    n_trajectories:
        Number of Morris trajectories.
    n_levels:
        Grid levels ``p`` (even, classic Morris; step ``delta = p/(2(p-1))``
        of the unit cube is used after scaling).
    """
    if n_trajectories < 1:
        raise ValueError("n_trajectories must be >= 1")
    if n_levels < 2:
        raise ValueError("n_levels must be >= 2")
    if len(bounds) != len(coeffs):
        raise ValueError("coeffs length must match bounds")
    n_dim = len(bounds)
    if n_dim < 1:
        raise ValueError("bounds must be non-empty")

    lows = np.array([float(b[0]) for b in bounds], dtype=float)
    highs = np.array([float(b[1]) for b in bounds], dtype=float)
    if np.any(highs <= lows):
        raise ValueError("each bound requires low < high")
    c = np.asarray(coeffs, dtype=float)
    rng = np.random.default_rng(seed)

    # Unit-cube Morris trajectories, then scale to bounds.
    p = int(n_levels)
    delta = p / (2.0 * (p - 1)) if p > 1 else 0.5
    effects = np.zeros((n_trajectories, n_dim), dtype=float)

    for t in range(n_trajectories):
        # Starting point on the p-level grid in [0,1]^k.
        grid = np.linspace(0.0, 1.0, p)
        x = np.array([float(rng.choice(grid)) for _ in range(n_dim)], dtype=float)
        order = rng.permutation(n_dim)
        for j in order:
            x_new = x.copy()
            # Reflect by ±delta within [0,1].
            step = delta if x[j] + delta <= 1.0 + 1e-12 else -delta
            if x[j] + step < -1e-12:
                step = delta
            x_new[j] = float(np.clip(x[j] + step, 0.0, 1.0))
            x_phys = lows + x * (highs - lows)
            x_new_phys = lows + x_new * (highs - lows)
            f0 = _eval_linear(x_phys, intercept, c)
            f1 = _eval_linear(x_new_phys, intercept, c)
            # Elementary effect scaled by physical step size.
            dx = x_new_phys[j] - x_phys[j]
            effects[t, j] = (f1 - f0) / dx if abs(dx) > 1e-15 else 0.0
            x = x_new

    mu = effects.mean(axis=0)
    mu_star = np.mean(np.abs(effects), axis=0)
    sigma = effects.std(axis=0, ddof=1) if n_trajectories > 1 else np.zeros(n_dim)

    return {
        "mu": [float(v) for v in mu.tolist()],
        "mu_star": [float(v) for v in mu_star.tolist()],
        "sigma": [float(v) for v in sigma.tolist()],
        "n_dim": n_dim,
        "n_trajectories": int(n_trajectories),
        "n_levels": p,
        "delta_unit": float(delta),
        "model": "linear",
        "seed": seed,
        "backend": "numpy",
        "converged": None,
    }
