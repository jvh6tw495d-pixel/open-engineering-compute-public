"""Monte Carlo estimators (NumPy RNG). Merit: NumPy."""

from __future__ import annotations

from typing import Any

import numpy as np

from oec.kernel.numerics.expressions import compile_expression


def monte_carlo_mean(
    expression: str,
    *,
    n_samples: int,
    low: float,
    high: float,
    seed: int | None = None,
    symbol: str = "x",
) -> dict[str, Any]:
    """Estimate E[f(X)] for X ~ Uniform(low, high) by sample mean.

    Uses restricted-AST expressions (same safety as other math skills).
    """
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    if high <= low:
        raise ValueError("high must be > low")
    fn = compile_expression(expression, symbol=symbol)
    rng = np.random.default_rng(seed)
    samples: Any = rng.uniform(low, high, size=int(n_samples))
    values = np.array([float(fn(float(x))) for x in samples], dtype=float)
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if n_samples > 1 else 0.0
    # 95% normal approx CI for the mean
    se = std / np.sqrt(n_samples) if n_samples > 0 else 0.0
    z = 1.959963984540054
    return {
        "mean": mean,
        "std": std,
        "stderr": float(se),
        "ci95_low": float(mean - z * se),
        "ci95_high": float(mean + z * se),
        "n_samples": int(n_samples),
        "low": float(low),
        "high": float(high),
        "seed": seed,
        "expression": expression,
        "backend": "numpy",
    }
