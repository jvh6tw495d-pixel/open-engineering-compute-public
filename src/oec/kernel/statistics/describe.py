"""Basic descriptive statistics (NumPy). Merit: NumPy."""

from __future__ import annotations

from typing import Any

import numpy as np


def describe(values: list[float]) -> dict[str, Any]:
    arr: Any = np.array(values, dtype=float)
    n = int(arr.size)
    if n == 0:
        raise ValueError("values must be non-empty")
    return {
        "n": n,
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if n > 1 else 0.0,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "median": float(np.median(arr)),
        "q25": float(np.quantile(arr, 0.25)),
        "q75": float(np.quantile(arr, 0.75)),
        "backend": "numpy",
    }
