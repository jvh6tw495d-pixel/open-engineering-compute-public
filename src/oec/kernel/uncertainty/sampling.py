"""Design-of-experiments samplers. Merit: NumPy (no SALib dependency)."""

from __future__ import annotations

from typing import Any

import numpy as np


def latin_hypercube(
    n_samples: int,
    bounds: list[list[float]],
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    """Latin Hypercube sample in a hyper-rectangle (McKay et al. 1979).

    ``bounds`` is a list of ``[low, high]`` pairs (one per dimension).
    Returns samples as an ``n_samples x n_dim`` matrix scaled to bounds.
    """
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    if not bounds:
        raise ValueError("bounds must be non-empty")
    lows: list[float] = []
    highs: list[float] = []
    for pair in bounds:
        if len(pair) != 2:
            raise ValueError("each bound must be [low, high]")
        lo, hi = float(pair[0]), float(pair[1])
        if not (lo < hi):
            raise ValueError("each bound requires low < high")
        lows.append(lo)
        highs.append(hi)

    n_dim = len(bounds)
    rng = np.random.default_rng(seed)
    # Stratified unit hypercube, then random permute per dimension.
    u = rng.uniform(size=(n_samples, n_dim))
    samples_unit = np.empty((n_samples, n_dim), dtype=float)
    for j in range(n_dim):
        # One sample per stratum, then shuffle strata order.
        strata = (np.arange(n_samples) + u[:, j]) / n_samples
        rng.shuffle(strata)
        samples_unit[:, j] = strata

    lows_a = np.asarray(lows, dtype=float)
    highs_a = np.asarray(highs, dtype=float)
    scaled = lows_a + samples_unit * (highs_a - lows_a)
    return {
        "samples": [[float(v) for v in row] for row in scaled.tolist()],
        "n_samples": int(n_samples),
        "n_dim": int(n_dim),
        "bounds": [[float(a), float(b)] for a, b in zip(lows, highs, strict=True)],
        "seed": seed,
        "backend": "numpy",
        "converged": None,
        "method": "latin_hypercube",
    }
