"""Matrix analysis helpers (NumPy). Merit: NumPy/LAPACK."""

from __future__ import annotations

from typing import Any

import numpy as np


def matrix_properties(a: list[list[float]]) -> dict[str, Any]:
    matrix: Any = np.array(a, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("A must be 2-D")
    m, n = int(matrix.shape[0]), int(matrix.shape[1])
    rank = int(np.linalg.matrix_rank(matrix))
    cond = float(np.linalg.cond(matrix)) if min(m, n) > 0 else float("inf")

    result: dict[str, Any] = {
        "shape": [m, n],
        "rank": rank,
        "condition_number": cond,
        "backend": "numpy",
    }

    # Eigenvalues only for square matrices
    if m == n and m > 0:
        eigvals: Any = np.linalg.eigvals(matrix)
        result["eigenvalues_real"] = [float(np.real(v)) for v in eigvals]
        result["eigenvalues_imag"] = [float(np.imag(v)) for v in eigvals]

    u: Any
    s: Any
    vh: Any
    u, s, vh = np.linalg.svd(matrix, full_matrices=False)
    result["singular_values"] = [float(val) for val in list(s)]
    result["svd_u_shape"] = [int(u.shape[0]), int(u.shape[1])]
    result["svd_vh_shape"] = [int(vh.shape[0]), int(vh.shape[1])]
    return result
